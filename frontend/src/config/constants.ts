/**
 * Application-wide constants.
 * Environment variables are read from the repo-root .env via Vite's envDir.
 */

/** Base URL for the Django REST Framework API */
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

/** Default pagination page size */
export const DEFAULT_PAGE_SIZE = 20;

/** JWT token storage keys (localStorage) */
export const ACCESS_TOKEN_KEY = 'lapd_access_token';
export const REFRESH_TOKEN_KEY = 'lapd_refresh_token';

/** Most-wanted threshold in days */
export const MOST_WANTED_DAYS_THRESHOLD = 30;

/** Reward multiplier constant (matches backend core.constants) */
export const REWARD_MULTIPLIER = 20_000_000;

/** Crime level display labels */
export const CRIME_LEVEL_LABELS: Record<number, string> = {
  1: 'Level 3 (Minor)',
  2: 'Level 2 (Medium)',
  3: 'Level 1 (Major)',
  4: 'Critical',
};

/** Routes that do not require authentication */
export const PUBLIC_ROUTES = ['/', '/most-wanted', '/login', '/register'];
