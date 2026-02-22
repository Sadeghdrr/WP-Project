// TODO: Define global constants

/** Base URL for the Django REST Framework API */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

/** Default pagination page size */
export const DEFAULT_PAGE_SIZE = 20;

/** JWT token storage keys */
export const ACCESS_TOKEN_KEY = 'access_token';
export const REFRESH_TOKEN_KEY = 'refresh_token';

/** Most-wanted threshold in days */
export const MOST_WANTED_DAYS_THRESHOLD = 30;

/** Crime level labels (matching backend CrimeLevel IntegerChoices) */
export const CRIME_LEVEL_LABELS: Record<number, string> = {
  1: 'Level 3 (Minor)',
  2: 'Level 2 (Medium)',
  3: 'Level 1 (Major)',
  4: 'Critical',
};
