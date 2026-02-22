"""
Core constants — **Single Source of Truth** for project-wide magic numbers.

Any formula or business rule that references a numeric constant should
import it from here instead of hardcoding.  This avoids drift between
apps that use the same value.
"""

# ── Reward Calculation ──────────────────────────────────────────────
# Multiplier used in the bounty reward formula (project-doc §4.7 Note 2):
#     reward = most_wanted_score × REWARD_MULTIPLIER
#
# The original formula was embedded as an image in the project document.
# The cases API report specifies 20,000,000 Rials as the multiplier.
REWARD_MULTIPLIER: int = 20_000_000  # Rials
