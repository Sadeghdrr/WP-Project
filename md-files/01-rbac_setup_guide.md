# RBAC Setup Guide

> Management command for seeding **Roles** and **Permissions** in the L.A. Noire police-department backend.

---

## How to Run

```bash
# From the backend directory (or wherever manage.py lives):
python manage.py setup_rbac
```

> **Important:** Make sure `makemigrations` and `migrate` have been run first so that Django's `Permission` table is fully populated.

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py setup_rbac
```

The command is **idempotent** — running it multiple times will not create duplicates. Existing roles are updated to match the mapping; permissions removed from the script are also removed from the role.

---

## Role → Permission Mapping

The table below shows which Django permission codenames are assigned to each role. Permissions follow the standard format `<action>_<model>` (e.g. `view_case`, `add_evidence`).

### System Admin (hierarchy: 100)

Full CRUD on **all** models.

| Model Area | Permissions                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Accounts   | `view_role` `add_role` `change_role` `delete_role` `view_user` `add_user` `change_user` `delete_user`                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Cases      | `view_case` `add_case` `change_case` `delete_case` `view_casecomplainant` `add_casecomplainant` `change_casecomplainant` `delete_casecomplainant` `view_casewitness` `add_casewitness` `change_casewitness` `delete_casewitness` `view_casestatuslog` `add_casestatuslog` `change_casestatuslog` `delete_casestatuslog`                                                                                                                                                                                                                                                   |
| Evidence   | `view_evidence` `add_evidence` `change_evidence` `delete_evidence` `view_testimonyevidence` `add_testimonyevidence` `change_testimonyevidence` `delete_testimonyevidence` `view_biologicalevidence` `add_biologicalevidence` `change_biologicalevidence` `delete_biologicalevidence` `view_vehicleevidence` `add_vehicleevidence` `change_vehicleevidence` `delete_vehicleevidence` `view_identityevidence` `add_identityevidence` `change_identityevidence` `delete_identityevidence` `view_evidencefile` `add_evidencefile` `change_evidencefile` `delete_evidencefile` |
| Suspects   | `view_suspect` `add_suspect` `change_suspect` `delete_suspect` `view_interrogation` `add_interrogation` `change_interrogation` `delete_interrogation` `view_trial` `add_trial` `change_trial` `delete_trial` `view_bountytip` `add_bountytip` `change_bountytip` `delete_bountytip` `view_bail` `add_bail` `change_bail` `delete_bail`                                                                                                                                                                                                                                    |
| Board      | `view_detectiveboard` `add_detectiveboard` `change_detectiveboard` `delete_detectiveboard` `view_boardnote` `add_boardnote` `change_boardnote` `delete_boardnote` `view_boarditem` `add_boarditem` `change_boarditem` `delete_boarditem` `view_boardconnection` `add_boardconnection` `change_boardconnection` `delete_boardconnection`                                                                                                                                                                                                                                   |
| Core       | `view_notification` `add_notification` `change_notification` `delete_notification`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

### Police Chief (hierarchy: 10)

| Model Area | Permissions                                                                                                                                                                                                                                                                                                                                  |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cases      | `view_case` `add_case` `change_case` `view_casecomplainant` `change_casecomplainant` `view_casewitness` `add_casewitness` `change_casewitness` `view_casestatuslog` `add_casestatuslog`                                                                                                                                                      |
| Evidence   | `view_evidence` `add_evidence` `change_evidence` `view_testimonyevidence` `add_testimonyevidence` `change_testimonyevidence` `view_biologicalevidence` `view_vehicleevidence` `add_vehicleevidence` `change_vehicleevidence` `view_identityevidence` `add_identityevidence` `change_identityevidence` `view_evidencefile` `add_evidencefile` |
| Suspects   | `view_suspect` `add_suspect` `change_suspect` `view_interrogation` `view_trial` `view_bountytip` `view_bail` `change_bail`                                                                                                                                                                                                                   |
| Board      | `view_detectiveboard` `view_boardnote` `view_boarditem` `view_boardconnection`                                                                                                                                                                                                                                                               |
| Accounts   | `view_user`                                                                                                                                                                                                                                                                                                                                  |
| Core       | `view_notification` `add_notification` `change_notification` `delete_notification`                                                                                                                                                                                                                                                           |

### Captain (hierarchy: 9)

| Model Area | Permissions                                                                                                                                      |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Cases      | `view_case` `add_case` `change_case` `view_casecomplainant` `change_casecomplainant` `view_casewitness` `view_casestatuslog` `add_casestatuslog` |
| Evidence   | `view_evidence` `view_testimonyevidence` `view_biologicalevidence` `view_vehicleevidence` `view_identityevidence` `view_evidencefile`            |
| Suspects   | `view_suspect` `change_suspect` `view_interrogation` `view_trial` `view_bountytip` `view_bail`                                                   |
| Board      | `view_detectiveboard` `view_boardnote` `view_boarditem` `view_boardconnection`                                                                   |
| Accounts   | `view_user`                                                                                                                                      |
| Core       | `view_notification` `add_notification` `change_notification` `delete_notification`                                                               |

### Sergeant (hierarchy: 8)

| Model Area | Permissions                                                                                                                                                        |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Cases      | `view_case` `change_case` `view_casecomplainant` `view_casewitness` `view_casestatuslog` `add_casestatuslog`                                                       |
| Evidence   | `view_evidence` `view_testimonyevidence` `view_biologicalevidence` `view_vehicleevidence` `view_identityevidence` `view_evidencefile`                              |
| Suspects   | `view_suspect` `change_suspect` `view_interrogation` `add_interrogation` `change_interrogation` `view_trial` `view_bountytip` `view_bail` `add_bail` `change_bail` |
| Board      | `view_detectiveboard` `view_boardnote` `view_boarditem` `view_boardconnection`                                                                                     |
| Accounts   | `view_user`                                                                                                                                                        |
| Core       | `view_notification` `add_notification` `change_notification` `delete_notification`                                                                                 |

### Detective (hierarchy: 7)

| Model Area | Permissions                                                                                                                                                                                                                                                                                                                                                                                 |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cases      | `view_case` `change_case` `view_casecomplainant` `view_casewitness` `add_casewitness` `change_casewitness` `view_casestatuslog` `add_casestatuslog`                                                                                                                                                                                                                                         |
| Evidence   | `view_evidence` `add_evidence` `change_evidence` `view_testimonyevidence` `add_testimonyevidence` `change_testimonyevidence` `view_biologicalevidence` `add_biologicalevidence` `view_vehicleevidence` `add_vehicleevidence` `change_vehicleevidence` `view_identityevidence` `add_identityevidence` `change_identityevidence` `view_evidencefile` `add_evidencefile` `change_evidencefile` |
| Suspects   | `view_suspect` `add_suspect` `change_suspect` `view_interrogation` `add_interrogation` `change_interrogation` `view_trial` `view_bountytip` `change_bountytip` `view_bail`                                                                                                                                                                                                                  |
| Board      | `view_detectiveboard` `add_detectiveboard` `change_detectiveboard` `delete_detectiveboard` `view_boardnote` `add_boardnote` `change_boardnote` `delete_boardnote` `view_boarditem` `add_boarditem` `change_boarditem` `delete_boarditem` `view_boardconnection` `add_boardconnection` `change_boardconnection` `delete_boardconnection`                                                     |
| Accounts   | `view_user`                                                                                                                                                                                                                                                                                                                                                                                 |
| Core       | `view_notification` `add_notification` `change_notification` `delete_notification`                                                                                                                                                                                                                                                                                                          |

### Police Officer (hierarchy: 6)

| Model Area | Permissions                                                                                                                                                                                                                                  |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cases      | `view_case` `add_case` `change_case` `view_casecomplainant` `view_casewitness` `add_casewitness` `change_casewitness` `view_casestatuslog` `add_casestatuslog`                                                                               |
| Evidence   | `view_evidence` `add_evidence` `view_testimonyevidence` `add_testimonyevidence` `view_biologicalevidence` `view_vehicleevidence` `add_vehicleevidence` `view_identityevidence` `add_identityevidence` `view_evidencefile` `add_evidencefile` |
| Suspects   | `view_suspect` `view_bountytip` `change_bountytip`                                                                                                                                                                                           |
| Accounts   | `view_user`                                                                                                                                                                                                                                  |
| Core       | `view_notification` `add_notification` `change_notification` `delete_notification`                                                                                                                                                           |

### Patrol Officer (hierarchy: 5)

| Model Area | Permissions                                                                                                                                                                                                        |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Cases      | `view_case` `add_case` `change_case` `view_casecomplainant` `view_casewitness` `add_casewitness` `change_casewitness` `view_casestatuslog` `add_casestatuslog`                                                     |
| Evidence   | `view_evidence` `add_evidence` `view_testimonyevidence` `add_testimonyevidence` `view_vehicleevidence` `add_vehicleevidence` `view_identityevidence` `add_identityevidence` `view_evidencefile` `add_evidencefile` |
| Suspects   | `view_suspect`                                                                                                                                                                                                     |
| Accounts   | `view_user`                                                                                                                                                                                                        |
| Core       | `view_notification` `add_notification` `change_notification` `delete_notification`                                                                                                                                 |

### Cadet (hierarchy: 4)

| Model Area | Permissions                                                                                                                           |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Cases      | `view_case` `change_case` `view_casecomplainant` `change_casecomplainant` `view_casewitness` `view_casestatuslog` `add_casestatuslog` |
| Evidence   | `view_evidence` `view_testimonyevidence` `view_evidencefile`                                                                          |
| Accounts   | `view_user`                                                                                                                           |
| Core       | `view_notification` `add_notification` `change_notification` `delete_notification`                                                    |

### Coroner (hierarchy: 3)

| Model Area | Permissions                                                                                                                                                                                            |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Cases      | `view_case`                                                                                                                                                                                            |
| Evidence   | `view_evidence` `change_evidence` `view_testimonyevidence` `view_biologicalevidence` `change_biologicalevidence` `view_vehicleevidence` `view_identityevidence` `view_evidencefile` `add_evidencefile` |
| Core       | `view_notification` `add_notification` `change_notification` `delete_notification`                                                                                                                     |

### Judge (hierarchy: 2)

| Model Area | Permissions                                                                                                                           |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Cases      | `view_case` `view_casecomplainant` `view_casewitness` `view_casestatuslog`                                                            |
| Evidence   | `view_evidence` `view_testimonyevidence` `view_biologicalevidence` `view_vehicleevidence` `view_identityevidence` `view_evidencefile` |
| Suspects   | `view_suspect` `view_interrogation` `view_trial` `add_trial` `change_trial` `view_bail`                                               |
| Accounts   | `view_user`                                                                                                                           |
| Core       | `view_notification` `add_notification` `change_notification` `delete_notification`                                                    |

### Complainant (hierarchy: 1)

| Permissions                                                                             |
| --------------------------------------------------------------------------------------- |
| `view_case` `add_case` `view_casecomplainant` `view_notification` `change_notification` |

### Witness (hierarchy: 1)

| Permissions                                           |
| ----------------------------------------------------- |
| `view_case` `view_notification` `change_notification` |

### Suspect (hierarchy: 0)

| Permissions                                                       |
| ----------------------------------------------------------------- |
| `view_case` `view_bail` `view_notification` `change_notification` |

### Criminal (hierarchy: 0)

| Permissions                                                       |
| ----------------------------------------------------------------- |
| `view_case` `view_bail` `view_notification` `change_notification` |

### Base User (hierarchy: 0)

| Permissions                                                                               |
| ----------------------------------------------------------------------------------------- |
| `view_suspect` `view_bountytip` `add_bountytip` `view_notification` `change_notification` |

---

## Adding New Permissions

As the project grows, follow these steps to extend the RBAC system:

### 1. Define the permission

If it's a **custom permission** (beyond Django's auto-generated CRUD), add it to the model's `Meta.permissions`:

```python
# In your app's models.py
class Case(TimeStampedModel):
    class Meta:
        permissions = [
            ("can_approve_case", "Can approve case"),
            ("can_close_case", "Can close case"),
        ]
```

Then run:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Add the codename to the mapping

Open `backend/accounts/management/commands/setup_rbac.py` and add the new codename to the relevant role(s) in the `ROLE_PERMISSIONS_MAP` dictionary:

```python
("Captain", "Approves cases and forwards them to the judiciary for trial.", 9): [
    # ... existing permissions ...
    "can_approve_case",    # ← new permission
    "can_close_case",      # ← new permission
],
```

### 3. Re-run the command

```bash
python manage.py setup_rbac
```

The command will update the role's permission set to include the new entries. Any permission codename that doesn't yet exist in the database will be skipped with a warning.

### 4. Adding a new role

To add an entirely new role, simply add a new entry to `ROLE_PERMISSIONS_MAP`:

```python
("New Role Name", "Description of the role.", <hierarchy_level>): [
    "view_case",
    "add_case",
    # ... other codenames
],
```

---

## Design Notes

- **Idempotent:** `get_or_create` prevents duplicate roles; `permissions.set()` ensures each role's permissions exactly match the script (stale permissions are automatically removed).
- **No hardcoded IDs:** All lookups use `name` (roles) and `codename` (permissions).
- **Hierarchy levels** encode relative authority: `Police Chief (10) > Captain (9) > Sergeant (8) > Detective (7) > Police Officer (6) > Patrol Officer (5) > Cadet (4) > Coroner (3) > Judge (2) > Complainant/Witness (1) > Base User/Suspect/Criminal (0)`. System Admin is at `100`.
- **Graceful degradation:** If a permission codename doesn't exist yet (e.g., migrations haven't run), the command prints a warning and skips it instead of crashing.
