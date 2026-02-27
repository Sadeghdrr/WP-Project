# Most-Wanted Aggregation & Unified Reward Calculations — Implementation Report

## 1. Final Formula Definition

### 1.1 Most-Wanted Eligibility

A suspect qualifies for the **Most Wanted** page when **all** of the following hold:

1. `Suspect.status == "wanted"`
2. `Suspect.wanted_since` is **strictly more than 30 days** ago (i.e., `days_wanted > 30`)
3. The suspect is linked to at least one **open** case (case status ∉ {`closed`, `voided`})

### 1.2 Ranking Score

$$
\text{score} = \max(L_j) \times \max(D_i)
$$

Where:

| Symbol | Meaning                                                                                     | Source                                                                     |
| ------ | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| $L_j$  | Days the suspect has been wanted in each _open_ case                                        | `(now - Suspect.wanted_since).days` for each eligible open Suspect row |
| $D_i$  | Crime degree (integer 1–4) of the highest-severity case the suspect has ever been linked to | `Case.crime_level` (1 = Level 3/Minor … 4 = Critical)                   |

The API now aggregates **one Most-Wanted row per `national_id`** (for non-empty national IDs):

$$
\text{computed\_score} = \max(L_j) \times \max(D_i)
$$

### 1.3 Bounty Reward

$$
\text{reward} = \text{score} \times 20{,}000{,}000 \; \text{Rials}
$$

The multiplier constant is defined once in `core/constants.py` as `REWARD_MULTIPLIER = 20_000_000`.

### 1.4 Per-Case Tracking Threshold (Cases API)

At the single-case level, the formula simplifies to:

$$
\text{threshold} = \text{crime\_level} \times \text{days\_since\_creation}
$$

$$
\text{case\_reward} = \text{threshold} \times 20{,}000{,}000
$$

---

## 2. Unification Strategy

### 2.1 Problem Statement

Previously, the reward/score formulas were duplicated in two places:

- **`suspects/models.py`** — Python `@property` methods (`most_wanted_score`, `reward_amount`)
- **`cases/services.py`** — `CaseCalculationService` methods (`calculate_tracking_threshold`, `calculate_reward`)

The GAP Analysis (§6.2) identified that the reward multiplier was inconsistent (10M vs 20M) between domains.

### 2.2 Solution: `RewardCalculatorService` (Single Source of Truth)

A new service class was introduced in **`core/services.py`**:

```
core.services.RewardCalculatorService
```

This class owns **all** mathematical primitives:

| Method                                               | Purpose                             |
| ---------------------------------------------------- | ----------------------------------- |
| `compute_days_wanted(wanted_since)`                  | Days between `wanted_since` and now |
| `compute_score(max_days, max_degree)`                | `max_days × max_degree`             |
| `compute_reward(score)`                              | `score × REWARD_MULTIPLIER`         |
| `is_most_wanted(days_wanted)`                        | `days_wanted > 30`                  |
| `compute_case_tracking_threshold(crime_level, days)` | `crime_level × max(days, 0)`        |
| `compute_case_reward(crime_level, days)`             | `threshold × REWARD_MULTIPLIER`     |

### 2.3 Consumer Delegation

| Consumer                                                | How it uses RewardCalculatorService                                                                                                                          |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Suspect.reward_amount` (model property)                | Calls `RewardCalculatorService.compute_reward(self.most_wanted_score)`                                                                                       |
| `CaseCalculationService.calculate_tracking_threshold()` | Delegates to `compute_case_tracking_threshold()`                                                                                                             |
| `CaseCalculationService.calculate_reward()`             | Delegates to `compute_case_reward()`                                                                                                                         |
| `SuspectProfileService.get_most_wanted_list()`          | Uses constants from `RewardCalculatorService.MOST_WANTED_THRESHOLD_DAYS` and annotates DB-level score/reward using `REWARD_MULTIPLIER` from `core.constants` |

This ensures that if the multiplier or threshold changes, it is updated in **one place** (`core/constants.py` for the multiplier, `RewardCalculatorService.MOST_WANTED_THRESHOLD_DAYS` for the 30-day rule).

---

## 3. Performance Notes

### 3.1 ORM Aggregation Strategy

`SuspectProfileService.get_most_wanted_list()` now computes aggregation by `national_id` using ORM subqueries:

```python
eligible = Suspect.objects.filter(
    status="wanted",
    wanted_since__lt=cutoff,  # strictly > 30 days ago
).exclude(
    case__status__in=["closed", "voided"],  # must have open case
).select_related("case")

max_days_subquery = (
    Suspect.objects.filter(national_id=OuterRef("national_id"), ...)
    .annotate(days_wanted=ExtractDay(Now() - F("wanted_since")))
    .values("national_id")
    .annotate(max_days=Max("days_wanted"))
    .values("max_days")[:1]
)
max_crime_subquery = (
    Suspect.objects.filter(national_id=OuterRef("national_id"))
    .values("national_id")
    .annotate(max_crime=Max("case__crime_level"))
    .values("max_crime")[:1]
)

grouped = eligible.exclude(national_id="").annotate(
    computed_days_wanted=Coalesce(
        Subquery(max_days_subquery, output_field=IntegerField()), Value(0)
    ),
    crime_degree=Coalesce(
        Subquery(max_crime_subquery, output_field=IntegerField()),
        F("case__crime_level"),
    ),
    computed_score=ExpressionWrapper(
        F("computed_days_wanted") * F("crime_degree"),
        output_field=IntegerField(),
    ),
    computed_reward=ExpressionWrapper(
        F("computed_days_wanted") * F("crime_degree") * Value(REWARD_MULTIPLIER),
        output_field=IntegerField(),
    ),
).order_by("national_id", "-computed_score", "id").distinct("national_id")
```

### 3.2 N+1 Avoidance

- **`select_related("case")`** keeps case joins efficient for display fields.
- **Aggregation primitives** (`max_days`, `max_crime`) are resolved via SQL subqueries per `national_id` rather than Python loops.
- The `MostWantedSerializer` reads annotated attributes via `getattr(obj, "computed_*", ...)` with fallback to model properties for backward compatibility.

### 3.3 Query Count

The endpoint runs the grouped query plus a fallback query for rows with blank `national_id` (if any), then merges and sorts in memory.

---

## 4. Files Changed

| File                      | Change Summary                                                                                            |
| ------------------------- | --------------------------------------------------------------------------------------------------------- |
| `core/services.py`        | Added `RewardCalculatorService` class with all formula primitives                                         |
| `cases/services.py`       | Updated `CaseCalculationService` to delegate to `RewardCalculatorService`                                 |
| `suspects/services.py`    | Rewrote `get_most_wanted_list()` to aggregate by `national_id` (`max_days × max_crime_level`) and keep open-case filtering |
| `suspects/serializers.py` | Updated `MostWantedSerializer` to use annotated fields + `calculated_reward` alias                        |
| `suspects/models.py`      | Updated `Suspect.reward_amount` property to delegate to `RewardCalculatorService`; fixed stale docstring  |
