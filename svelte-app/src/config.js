// Production is served by FastAPI; the dev server runs on port 5001.
export const API_BASE_URL = window.location.port === '5001'
    ? `${window.location.protocol}//${window.location.hostname}:5000`
    : window.location.origin;
