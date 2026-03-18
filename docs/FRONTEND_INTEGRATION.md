# Frontend and Mobile Integration Guide

This document is the implementation handoff for teams integrating web or mobile clients with the Athelix API.

It focuses on:

- How to initialize the client
- How to authenticate users
- How to map screens/features to backend endpoints
- What payload conventions to follow
- How to handle errors, tokens, analytics, and optional mesocycle flows

## 1. Base Conventions

### Base URL

Use the deployed API origin, for example:

```text
https://api.example.com
```

Local development:

```text
http://localhost:8000
```

### Content Type

Send and accept JSON:

```http
Content-Type: application/json
Accept: application/json
```

### Authentication Header

For authenticated endpoints:

```http
Authorization: Bearer <access_token>
```

### Date and Time Rules

- `datetime` fields are ISO 8601 timestamps
- `date` fields are plain ISO dates (`YYYY-MM-DD`)
- Store timestamps in UTC on the client when possible
- Convert to local display time only in the UI layer

## 2. Client Bootstrap Flow

On application startup, call:

```http
GET /meta/app-config
```

Use this response to drive client-side configuration:

- app name and version display
- token lifetime handling
- supported e1RM formulas
- supported PR record types
- supported mesocycle goals
- docs/OpenAPI links for development tooling

Recommended launch sequence:

1. Fetch `GET /meta/app-config`
2. Restore tokens from secure storage if present
3. If access token exists, call `GET /auth/me`
4. If access token is expired but refresh token exists, call `POST /auth/refresh`
5. After auth succeeds, call `GET /users/me/overview`

## 3. Authentication Integration

### Registration

```http
POST /auth/register
```

Request:

```json
{
  "username": "athlete_one",
  "email": "athlete@example.com",
  "password": "StrongPass123"
}
```

### Login

```http
POST /auth/login
```

### Refresh

```http
POST /auth/refresh
```

Request:

```json
{
  "refresh_token": "<refresh_token>"
}
```

### Auth Response Handling

Registration, login, and refresh all return:

- `access_token`
- `refresh_token`
- `token_type`
- `expires_in`
- `refresh_expires_in`
- `user`

Recommended client behavior:

- Store the access token in memory
- Store the refresh token in secure persistent storage
- Refresh proactively shortly before `expires_in`
- On `401 Could not validate credentials`, attempt one refresh and retry once
- If refresh fails, clear session and redirect to login

## 4. Error Handling Contract

HTTP errors use a predictable shape:

```json
{
  "detail": "Workout session not found",
  "message": "Workout session not found",
  "status_code": 404,
  "path": "/workout-sessions/123"
}
```

Validation errors also include `field_errors`:

```json
{
  "detail": [...],
  "message": "Validation error",
  "status_code": 422,
  "path": "/auth/register",
  "field_errors": [
    {
      "scope": "body",
      "field": "email",
      "message": "String should match pattern ...",
      "type": "string_pattern_mismatch"
    }
  ]
}
```

Recommended UI behavior:

- Use `message` for generic toast/snackbar feedback
- Use `field_errors` to map validation failures to form fields
- Use `status_code` to drive retry/logout flows

## 5. Home and Dashboard Screen

Use:

```http
GET /users/me/overview
```

This endpoint is designed specifically to reduce frontend fan-out on the app home screen.

It returns:

- `user`
- `has_profile`
- `profile`
- `latest_body_weight_log`
- `active_mesocycle`
- `latest_completed_session`
- `recent_personal_records`
- `workout_streaks`
- `stats`

Suggested screen usage:

- Header/profile card: `user`, `profile`
- Home metrics cards: `stats`
- Active block banner: `active_mesocycle`
- Recent activity card: `latest_completed_session`
- Achievement section: `recent_personal_records`
- Habit/streak widget: `workout_streaks`

## 6. User Account and Profile

### Current User

```http
GET /users/me
PATCH /users/me
```

Use `PATCH /users/me` for account settings screens.

### Profile

```http
GET /users/me/profile
PUT /users/me/profile
```

Frontend guidance:

- Treat `404 User profile not found` as “profile not created yet”, not an application failure
- Use `PUT` as an upsert
- Keep the client form model aligned with the profile schema

### Bodyweight Tracking

```http
GET /users/me/body-weight-logs
POST /users/me/body-weight-logs
GET /users/me/body-weight-logs/{log_id}
PATCH /users/me/body-weight-logs/{log_id}
DELETE /users/me/body-weight-logs/{log_id}
```

Suggested UI pattern:

- History list from `GET`
- Add/edit modal from `POST` and `PATCH`
- Use the returned object to update local state optimistically

## 7. Exercise Catalog

### Endpoints

```http
GET /exercises
GET /exercises/filters
GET /exercises/{exercise_id}
```

### Client Notes

- `GET /exercises` is paginated with `limit`, `offset`, and `total`
- Use `/exercises/filters` once to hydrate filter controls
- Use `/exercises/{exercise_id}` for full detail screens
- The catalog is authenticated in this backend

Recommended flow:

1. Fetch filters once and cache them
2. Fetch paginated exercises using current filters
3. Open details lazily on selection

## 8. Workout Templates

### Endpoints

```http
GET /workout-templates
POST /workout-templates
GET /workout-templates/{template_id}
PATCH /workout-templates/{template_id}
DELETE /workout-templates/{template_id}

GET /workout-templates/{template_id}/exercises
POST /workout-templates/{template_id}/exercises
GET /workout-templates/{template_id}/exercises/{template_exercise_id}
PATCH /workout-templates/{template_id}/exercises/{template_exercise_id}
DELETE /workout-templates/{template_id}/exercises/{template_exercise_id}
```

### UI Mapping

- Template list screen: `GET /workout-templates`
- Template detail builder: `GET /workout-templates/{template_id}`
- Add exercise workflow:
  1. Search exercise catalog
  2. Add selected exercise to template
  3. Save target sets/reps/RPE/rest/notes

Client-side recommendation:

- Maintain exercise order locally using `order_index`
- When reordering, patch each changed item explicitly

## 9. Workout Sessions and Set Logging

### Endpoints

```http
GET /workout-sessions
POST /workout-sessions
GET /workout-sessions/{session_id}
PATCH /workout-sessions/{session_id}
DELETE /workout-sessions/{session_id}

GET /workout-sessions/{session_id}/sets
POST /workout-sessions/{session_id}/sets
GET /workout-sessions/{session_id}/sets/{set_id}
PATCH /workout-sessions/{session_id}/sets/{set_id}
DELETE /workout-sessions/{session_id}/sets/{set_id}
```

### Recommended Session Flow

1. Create a session with `POST /workout-sessions`
2. Log sets incrementally with `POST /workout-sessions/{session_id}/sets`
3. Update session metadata like mood/location/notes as needed
4. Mark as complete by sending `finished_at` or `is_completed=true`

Important behavior:

- PR recalculation is triggered automatically from completed sessions
- Adding or editing a set in a completed session updates records automatically
- A session may optionally reference a `template_id`
- A session may optionally reference a `mesocycle_id`

Mobile recommendation:

- Keep local draft state while the user is in-session
- Persist each set as soon as the user confirms it
- On intermittent connectivity, queue failed writes and replay carefully

## 10. Personal Records

### Endpoints

```http
GET /personal-records
GET /personal-records/{record_id}
```

### Client Notes

- These records are derived, not manually created
- Filter by `exercise_id` and `record_type`
- Use for PR screens, badges, and achievement histories

Common record types are available from:

```http
GET /meta/app-config
```

## 11. Exercise Progress and Analytics

### Exercise Progress

```http
GET /progress/{exercise_id}
```

This endpoint returns:

- e1RM history
- volume history
- weekly volume
- progressive overload comparisons
- workout streaks

Suggested UI usage:

- Progress chart: `e1rm_history`, `weekly_volume_history`
- Comparison widget: `progressive_overload`
- Habit card: `workout_streaks`

### Muscle Balance

```http
GET /analytics/muscle-balance
```

Optional query params:

- `weeks`
- `reference_date`
- `mesocycle_id`

This report counts non-warmup working sets and compares average weekly sets per muscle group against configured minimums.

## 12. Mesocycles

Mesocycles are optional. The frontend should not require them for users who only want simple workout logging.

### Endpoints

```http
GET /mesocycles
POST /mesocycles
GET /mesocycles/{mesocycle_id}
PATCH /mesocycles/{mesocycle_id}
DELETE /mesocycles/{mesocycle_id}
GET /mesocycles/{mesocycle_id}/analytics
```

### UI Recommendation

Use mesocycles as an advanced planning feature:

- beginner/simple mode: hide mesocycle flows
- advanced mode: expose block planning and block analytics

### Analytics Response Use Cases

`GET /mesocycles/{mesocycle_id}/analytics` can power:

- training block summary cards
- previous-vs-current block comparison
- per-exercise block deltas
- deload recommendation banners
- block-specific muscle balance reports

## 13. Recommended Client Modules

Suggested service split on the frontend:

- `authApi`
- `metaApi`
- `userApi`
- `exerciseApi`
- `templateApi`
- `sessionApi`
- `recordApi`
- `progressApi`
- `mesocycleApi`
- `analyticsApi`

Suggested app state slices:

- auth state
- current user state
- exercise catalog cache
- template library
- active workout session
- analytics cache
- mesocycle planning

## 14. Suggested Screen-to-Endpoint Mapping

### Splash / bootstrap

- `GET /meta/app-config`
- `GET /auth/me` or `POST /auth/refresh`

### Home

- `GET /users/me/overview`

### Profile

- `GET /users/me`
- `GET /users/me/profile`
- `PUT /users/me/profile`

### Bodyweight

- `GET /users/me/body-weight-logs`
- `POST /users/me/body-weight-logs`
- `PATCH /users/me/body-weight-logs/{log_id}`

### Exercise explorer

- `GET /exercises/filters`
- `GET /exercises`
- `GET /exercises/{exercise_id}`

### Templates

- `GET /workout-templates`
- `GET /workout-templates/{template_id}`
- template exercise CRUD endpoints

### Active workout

- `POST /workout-sessions`
- set CRUD endpoints
- `PATCH /workout-sessions/{session_id}`

### Progress

- `GET /progress/{exercise_id}`
- `GET /personal-records`
- `GET /analytics/muscle-balance`

### Mesocycle planning

- mesocycle CRUD endpoints
- `GET /mesocycles/{mesocycle_id}/analytics`

## 15. Offline and Sync Considerations

The current backend is online-first. For mobile clients:

- cache read-heavy resources like exercises, templates, and app config
- queue mutating workout actions when connectivity is lost
- replay writes in order for session/set mutations
- avoid parallel conflicting updates for the same session

Recommended conflict rule:

- server is the source of truth
- after replaying queued writes, refetch the affected session

## 16. Development and Debugging

Useful URLs in local development:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

Recommended frontend developer workflow:

1. Start the backend locally
2. Inspect `/meta/app-config`
3. Import the OpenAPI schema if your client stack supports it
4. Build the auth layer first
5. Build `GET /users/me/overview` next
6. Add feature modules screen by screen

## 17. Product Scope Notes

For the current MVP, the backend is functionally complete for personal workout tracking and analytics.

Not yet included:

- password reset
- email verification
- push notifications
- coach-athlete multi-user relationships
- file uploads/media attachments
- billing/subscription flows
- advanced background job infrastructure

Those should be treated as future product expansion, not blockers for integrating the current app.
