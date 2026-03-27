# Todo Application -- Architecture Plan

Revision 3 -- static files served from disk via `⎕NGET`; `OnErrorFn` for HTML error responses.

## Overview

A classic todo application with an htmx front-end and a Dyalog APL back-end, using the Stark REST router on top of Jarvis.

htmx works by exchanging HTML fragments with the server rather than JSON. The browser issues AJAX requests via htmx attributes; the server returns rendered HTML which htmx swaps into the DOM. This means the APL back-end is responsible for data and presentation: API handlers return HTML character vectors, not JSON namespaces.

Static assets (the shell page, CSS) live as ordinary files in `static/` and are read from disk with `⎕NGET` on each request. This keeps markup in its natural format, editable with standard tooling, and avoids encoding HTML inside APL source.

## Technology Stack

| Layer       | Technology                         |
|-------------|------------------------------------|
| Front-end   | HTML + htmx (CDN)                  |
| HTTP server | Jarvis (Dyalog APL)               |
| Routing     | Stark REST router                  |
| Language    | Dyalog APL 20.0+                  |
| Data store  | In-memory (APL namespace)          |

## Project Layout

```
/
  APLSource/
    TodoApp.aplc          -- main application class
    Render/               -- HTML rendering namespace (directory form)
      Render.apln         -- namespace header
      Escape.aplf         -- HTML entity escaping
      TodoItem.aplf       -- single <li> fragment
      TodoList.aplf       -- full list content
      RespondHTML.aplf     -- helper: set content-type and return HTML
  static/
    index.html            -- shell page, loads htmx from CDN
    style.css             -- minimal styling
  Run.apls                -- entry-point script
  tests/
    Unit/                 -- unit tests (rendering, data ops, escaping)
    Integration/          -- HTTP-level tests via HttpCommand
```

## Data Model

A single in-memory collection. Each todo is a namespace with three fields:

| Field       | Type      | Description                        |
|-------------|-----------|------------------------------------|
| `id`        | integer   | Auto-incrementing identifier       |
| `title`     | string    | The todo text                      |
| `completed` | boolean   | 0 = open, 1 = done                |

Storage is a vector of these namespaces held on the application class, with a counter for the next id. IDs are never reused after deletion. No persistence beyond the process lifetime -- this is a demo application.

### Threading

The router will use `ThreadMode←0` (single-threaded, all requests handled on the main thread). This eliminates concurrency concerns around shared mutable state. Appropriate for a demo; a production application would need `:Hold` tokens or similar synchronisation.

## REST API

API endpoints return `text/html` fragments. Static file endpoints return content with the appropriate MIME type derived from the file extension. Every handler uses the `RespondHTML` helper or sets the content-type via `req.SetContentType` before returning.

| Method   | Path              | Action                          | Returns                                | Errors                     |
|----------|-------------------|---------------------------------|----------------------------------------|----------------------------|
| `GET`    | `/`               | Serve the shell page            | Full HTML page (`static/index.html`)   |                            |
| `GET`    | `/style.css`      | Serve the stylesheet            | CSS file (`static/style.css`)          |                            |
| `GET`    | `/todos`          | List all todos                  | HTML fragment: list of items           |                            |
| `POST`   | `/todos`          | Create a new todo               | HTML fragment: new `<li>` item         | 400 if title missing/empty |
| `PUT`    | `/todos/{id}`     | Toggle completed state          | HTML fragment: updated `<li>`          | 400 invalid id, 404 not found |
| `DELETE` | `/todos/{id}`     | Remove a todo                   | Empty body, 200 status                 | 400 invalid id, 404 not found |

### Static file serving

Jarvis's `HTMLInterface` only works in JSON paradigm; Stark forces REST paradigm. Therefore, `HTMLInterface` cannot be used.

Instead, static assets are stored as plain files in `static/` and served by explicit Stark routes. Each handler reads the file from disk using `⎕NGET` and sets the content-type using Jarvis's built-in `ContentTypeForFile` method (which maps file extensions to MIME types via a 79-entry lookup table):

```apl
result←ServeFile req;path;content
  path←staticRoot,'index.html'
  content←⊃⎕NGET path 0          ⍝ read entire file as a character vector (flag 0)
  req.SetContentType req.ContentTypeForFile path
  result←content
```

`⎕NGET` with a flags argument of `0` returns a 3-element vector: `(content encoding newline)`. The `⊃` (first/disclose) extracts the content as a simple character vector. This is the natural fit for serving text files.

The `staticRoot` field on `TodoApp` is resolved at construction time relative to the script's location, so the application works regardless of the working directory.

For this demo, routes are registered explicitly for each static file (`/` and `/style.css`). A production application might use a catch-all handler that maps URL paths to files within a directory, but Stark does not support wildcard routes, and explicit registration is clearer for a small number of assets.

### Path parameter handling

Path parameters extracted by Stark are always strings. Handlers that accept `{id}` must convert to integer using `⎕VFI` and validate:

```apl
(valid id)←⎕VFI req.PathParams.id
:If ~valid
    req.Fail 400
    result←'' RespondHTML req
    :Return
:EndIf
id←⊃id
```

### Request payload handling

htmx forms submit as `application/x-www-form-urlencoded` by default. Jarvis parses this into a `Payload` namespace, but each field value is a nested vector (because Jarvis accumulates values to handle repeated field names). Handlers must unwrap with disclose:

```apl
title←⊃req.Payload.title
```

The plan deliberately avoids the `json-enc` htmx extension to keep the front-end dependency-free beyond htmx itself.

## Error Handling via OnErrorFn

Stark's `OnErrorFn` mechanism provides a centralised error handler for unhandled exceptions in route handlers. We use this to return HTML error responses consistent with the application's content type, rather than letting Jarvis return a bare 500 with no body.

### Configuration

```apl
router.OnErrorFn←'HandleError'
```

Set on the router before `Start`. Stark validates at startup that the named function exists in the `Handlers` namespace, is dyadic, and returns a result.

### Signature

```apl
result←err HandleError req
```

- `err` -- a plain namespace cloned from `⎕DMX` before `req.Fail` is called. Contains `EN` (error number), `EM` (error message), and `Message` (full text).
- `req` -- the Jarvis request object. Stark has already called `req.Fail 500` before invoking the handler.
- `result` -- the response body. Since we return HTML, we call `RespondHTML` here.

### Implementation

```apl
result←err HandleError req
  :Access Public
  html←'<div class="error">Something went wrong</div>'
  result←html RespondHTML req
```

The error handler deliberately does not expose `err.Message` to the client (information leakage). In debug mode (`Debug←1`), `OnErrorFn` is bypassed entirely and errors propagate to the APL session for inspection.

### Error responses from handlers vs OnErrorFn

Anticipated errors (missing todo, invalid id, empty title) are handled explicitly within each handler using `req.Fail` with the appropriate status code (400, 404). `OnErrorFn` catches only unexpected errors -- programming mistakes, system failures, or edge cases not covered by explicit validation. This separation keeps handler code focused on business logic while providing a safety net.

## Front-end Design

### index.html (static file)

A plain HTML file in `static/` containing:

1. A `<link>` to `/style.css`.
2. A `<script>` tag loading htmx from CDN.
3. A heading.
4. A form for adding todos, using `hx-post="/todos"` with `hx-target="#todo-list"` and `hx-swap="beforeend"`. The form resets itself after submission via `hx-on::after-request="this.reset()"`.
5. A `<ul id="todo-list">` container with `hx-get="/todos"` and `hx-trigger="load"` to populate on page load.

### style.css (static file)

Minimal CSS in `static/`: strikethrough for `.completed span`, basic layout, cursor pointer on interactive elements, error styling.

### Todo item fragment

Each todo is rendered as an `<li>` with a stable `id="todo-{id}"` attribute. All user-supplied text is HTML-escaped before embedding.

```html
<li id="todo-3" class="completed">
  <span hx-put="/todos/3" hx-target="#todo-3" hx-swap="outerHTML">Buy milk</span>
  <button hx-delete="/todos/3" hx-target="#todo-3" hx-swap="delete">x</button>
</li>
```

- Clicking the `<span>` sends a PUT to toggle completion.
- Clicking the delete button sends a DELETE; `hx-swap="delete"` removes the element from the DOM regardless of the response body.
- The `completed` class is toggled server-side; CSS applies strikethrough styling.

### Direct navigation to fragment endpoints

If a user navigates directly to `/todos` in the browser (rather than via htmx), they receive a bare HTML fragment without page chrome. This is standard htmx behaviour and acceptable for a demo. A production application could check the `HX-Request` header and return a full page for non-htmx requests; noted as a future enhancement.

## APL Implementation

### TodoApp.aplc (class)

Fields:
- `router` -- Stark instance
- `todos` -- vector of todo namespaces
- `nextId` -- integer counter
- `staticRoot` -- absolute path to the `static/` directory, resolved at construction time

Constructor:
1. Initialise `todos←⍬` and `nextId←1`.
2. Resolve `staticRoot` relative to the source file location.
3. Create Stark router, set `Handlers←⎕THIS`.
4. Set `router.ThreadMode←0`.
5. Set `router.OnErrorFn←'HandleError'`.
6. Register the six routes listed above.

Handler functions:

- `ServePage req` -- read `static/index.html` via `⎕NGET`, set content-type via `ContentTypeForFile`, return content.
- `ServeCSS req` -- read `static/style.css` via `⎕NGET`, set content-type via `ContentTypeForFile`, return content.
- `ListTodos req` -- render all todos via `Render.TodoList`, return joined HTML.
- `CreateTodo req` -- unwrap `⊃req.Payload.title`, validate non-empty, append new todo, return its `<li>` via `Render.TodoItem`. Return 400 if title is missing or empty.
- `ToggleTodo req` -- convert `req.PathParams.id` via `⎕VFI`, validate, find todo, flip `completed`, return updated `<li>`. Return 400 for invalid id, 404 for missing todo.
- `DeleteTodo req` -- convert and validate id, remove from `todos` vector, return empty body. Return 400 for invalid id, 404 for missing todo.
- `HandleError req` -- `OnErrorFn` target. Return a generic HTML error fragment. Do not expose internal error details to the client.

### Render namespace

Directory-form namespace (`Render/`) with individual `.aplf` files. Pure functions that accept data and return HTML character vectors. Isolating rendering from handlers makes unit testing straightforward.

- `RespondHTML` -- dyadic helper: `html RespondHTML req` calls `req.SetContentType 'text/html; charset=utf-8'` and returns `html`. Every API handler uses this as its last step, eliminating the risk of forgetting to set the content-type.
- `Escape text` -- replaces `&`, `<`, `>`, `"`, `'` with their HTML entity equivalents. Applied to all user-supplied text before embedding in HTML.
- `TodoItem todo` -- returns the `<li>` fragment for a single todo, with escaped title.
- `TodoList todos` -- returns the concatenation of `TodoItem` applied to each todo.

### Returning HTML from Stark handlers

Every API handler follows this pattern:

```apl
result←ListTodos req
  html←Render.TodoList todos
  result←html RespondHTML req
```

Static file handlers follow a different pattern -- they set the content-type from the file extension rather than hardcoding `text/html`:

```apl
result←ServePage req;path;content
  path←staticRoot,'index.html'
  content←⊃⎕NGET path 0
  req.SetContentType req.ContentTypeForFile path
  result←content
```

Note: returning a character vector rather than a namespace departs from the documented Stark handler contract ("returns a namespace"). This works because Jarvis's `ToJSON` is bypassed when the content-type is not `application/json`, and `Respond` sends `Response.Payload` as-is.

### OpenAPI spec

Stark auto-generates an OpenAPI spec at `/openapi.json` assuming `application/json` response types. This spec will be inaccurate for our HTML-returning endpoints. Known cosmetic issue; the endpoint remains available but is not authoritative for this application.

## Entry Point (Run.apls)

A dyalogscript following the pattern established in Stark's own examples:

1. Initialise `⎕IO←1` and load `StartupSession.aplf` from the Dyalog installation.
2. Use `⎕SE.Link.Import` to load Stark and Jarvis into `#`.
3. Use `⎕SE.Link.Import` to load the application source (`TodoApp.aplc`, `Render/`).
4. Instantiate `TodoApp` and call `Start` on a configurable port (default 8080).
5. Wait for shutdown signal.

## Testing Strategy

### Unit tests

- **Render.Escape**: verify that `&`, `<`, `>`, `"`, `'` are correctly escaped; verify pass-through of safe strings; verify empty input.
- **Render.TodoItem**: verify correct `<li>` output for completed and incomplete todos; verify that the title is escaped (inject `<script>` in title, confirm it appears as `&lt;script&gt;`).
- **Render.TodoList**: verify empty list, single item, multiple items.
- **Data operations**: verify that creating, toggling, and deleting todos mutates the collection correctly and returns expected values.

### Integration tests

- Use `HttpCommand` (included in Stark's test infrastructure) to make real HTTP requests against a running instance.
- Verify correct status codes and content-type headers for each endpoint.
- Verify that `GET /` returns `text/html` with content matching `index.html`.
- Verify that `GET /style.css` returns `text/css`.
- Verify HTML fragment content for API endpoints.
- Verify the full CRUD cycle end-to-end: create, list, toggle, delete.
- **Error cases**: POST with missing/empty title (expect 400), PUT/DELETE with non-numeric id (expect 400), PUT/DELETE with non-existent id (expect 404).
- **OnErrorFn**: trigger an unexpected error (e.g., via a deliberately broken handler in test setup), verify the response is 500 with an HTML body, not a bare error or JSON.
- **XSS**: POST a todo with `<script>` in the title, verify the response contains escaped entities.
- **Content-type**: verify no API endpoint leaks `application/json` content-type.

## Scope Boundaries

In scope:
- CRUD operations on in-memory todos
- htmx-driven UI with no custom JavaScript (beyond htmx itself)
- Static files served from disk via `⎕NGET`
- Input validation and error responses
- Centralised error handling via `OnErrorFn`
- HTML escaping of user input (XSS prevention)

Out of scope (unless later requested):
- Persistent storage (database, file-based)
- Authentication
- Multiple todo lists or users
- Editing todo titles after creation
- Drag-and-drop reordering
- Full-page responses for non-htmx requests (HX-Request header checking)
- Accurate OpenAPI spec for HTML endpoints

## Review Log

| Date       | Revision | Notes                                                    |
|------------|----------|----------------------------------------------------------|
| 2026-03-26 | 1        | Initial draft                                            |
| 2026-03-26 | 2        | Revised per adversarial review (docs/reviews/architecture.md). Removed HTMLInterface, inline all markup in APL, added RespondHTML helper, HTML escaping, form-urlencoded unwrapping, path param validation, error cases, ThreadMode 0, expanded tests. |
| 2026-03-26 | 3        | Static files restored to `static/` directory, served via `⎕NGET` and explicit routes. Added `OnErrorFn` for centralised HTML error responses. Removed `Render.Page` (replaced by `index.html` on disk). Added `ContentTypeForFile` for MIME type resolution. Added `staticRoot` field. Added OnErrorFn integration test. |
