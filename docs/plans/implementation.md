# Todo Application -- Implementation Plan

Revision 2 -- addressing findings from docs/reviews/implementation.md.

Derived from docs/plans/architecture.md (revision 3). Phased, test-first, each phase independently verifiable.

## Conventions

This project follows the Stark test infrastructure patterns:

- Test functions are niladic tradfns: `r←Test_Name dummy` returning `1` (pass) or `0` (fail).
- Test names begin with `Test_`.
- Unit tests call APL functions directly; integration tests use `HttpCommand` over HTTP.
- A `RunTests.apls` script discovers and runs all `Test_*` functions via a `RunHelper` namespace.
- `MockRequest` provides a lightweight stand-in for the Jarvis request object in unit tests.

Each phase below lists what to build, then the tests that gate the phase. No phase is complete until all its tests pass and there are no regressions in earlier phases. Run the full test suite before and after each phase.

## Resolved design decisions

These were identified as open in the review and are now settled:

1. **`staticRoot` resolution**: the `TodoApp` constructor receives `staticRoot` as its constructor argument. `Run.apls` (and `RunTests.apls`) computes the absolute path before instantiation. This avoids the class needing to discover its own source location at runtime.

2. **`todos` and `nextId` are `:Field Public Instance`** to allow unit tests to inspect internal state. Pragmatic for a demo application.

3. **`FindTodo` return convention**: returns `¯1` (negative one, a scalar integer) on error, or the positive index into `todos` on success. Callers check `:If ¯1=idx`. This is unambiguous -- indices are always positive.

4. **`⎕VFI` validation pattern**: must check that the input produces exactly one token and that it is valid. The correct pattern is:
   ```apl
   (valid values)←⎕VFI req.PathParams.id
   :If (1≠≢valid)∨(~⊃valid)
       req.Fail 400
       result←'<div class="error">Invalid id</div>' ##.Render.RespondHTML req
       :Return
   :EndIf
   id←⊃values
   ```
   This handles multi-token input (`'1 2'`), empty strings, and non-numeric values.

5. **Missing field check**: use `0=req.Payload.⎕NC⊂'title'` (name class 0 means not found). The previous plan incorrectly used `9.1`.

6. **Error response bodies**: all error paths (400, 404) return an HTML fragment via `RespondHTML` containing a `<div class="error">` with a user-facing message. This keeps the content-type consistent and gives htmx content to swap.

7. **`/test/break` route for OnErrorFn testing**: `TodoApp` exposes a public method `RegisterTestRoutes` that adds `/test/break` pointing to a private `_BrokenHandler` method (which signals EN 11). The test runner calls this after construction; `Run.apls` does not.

8. **HttpCommand POST syntax for form-urlencoded data**: `HttpCommand.Do` auto-detects `application/x-www-form-urlencoded` when the `Params` argument is a simple character vector that does not look like JSON (confirmed in HttpCommand source lines 550-554). So the correct call is simply:
   ```apl
   resp←#.HttpCommand.Do 'POST' url 'title=Buy milk'
   ```
   No explicit content-type argument needed. The 4th positional argument to `Do` is `Headers`, not content-type.

---

## Phase 1: Project scaffolding and test runner

Goal: a working test harness with a single trivial test, runnable via `dyalogscript RunTests.apls`.

### Build

1. Create directory structure:
   ```
   APLSource/
     Render/
       Render.apln
   static/
   tests/
     Unit/
     Integration/
     Mocks/
       MockRequest.aplc
     RunHelper.apln
   RunTests.apls
   ```

2. `RunHelper.apln` -- copy the pattern from Stark's `Tests/RunHelper.apln`. A `Run` function that discovers `Test_*` functions in a namespace, calls each, prints PASS/FAIL/ERROR, returns `(passed failed)`.

3. `MockRequest.aplc` -- a mock of the Jarvis request object. Full specification:

   **Fields:**
   ```apl
   :Field Public Instance Method←''
   :Field Public Instance Endpoint←''
   :Field Public Instance Payload←''
   :Field Public Instance PathParams
   :Field Public Instance QueryParams←0 2⍴0
   :Field Public Instance StatusCode←200
   :Field Public Instance Response
   ```

   **Constructor** (takes `(Method Endpoint)` pair):
   ```apl
   ∇ make args
     :Access Public
     :Implements Constructor
     (Method Endpoint)←args
     Payload←⎕NS ''
     PathParams←⎕NS ''
     Response←⎕NS ''
     Response.(Status StatusText Payload)←0 'OK' ''
     Response.Headers←0 2⍴'' ''
   ∇
   ```

   **`Fail` method:**
   ```apl
   ∇ {r}←{message}Fail status
     :Access Public Instance
     Response.Status←status
     r←⍬
   ∇
   ```

   **`SetContentType` method** (matches Jarvis signature at Jarvis.aplc line 1741):
   ```apl
   ∇ {r}←SetContentType contentType
     :Access Public Instance
     ⍝ Add or replace Content-Type in Response.Headers
     mask←Response.Headers[;1]≡¨⊂'Content-Type'
     :If ∨/mask
         Response.Headers[mask⍳1;2]←⊂contentType
     :Else
         Response.Headers⍪←'Content-Type' contentType
     :EndIf
     r←'Content-Type' contentType
   ∇
   ```

   **`ContentTypeForFile` method** (simplified version of Jarvis.aplc line 1763):
   ```apl
   ∇ r←ContentTypeForFile path;ext;types
     :Access Public Instance
     ext←⎕C 2⊃'.'(≠⊆⊢)⊃⌽1 ⎕NPARTS path
     types←⍉↑('html' 'text/html')('css' 'text/css')('js' 'text/javascript')('json' 'application/json')
     :If (⊂ext)∊types[1;]
         r←types[2;types[1;]⍳⊂ext]
     :Else
         r←'application/octet-stream'
     :EndIf
     r,←(r≡'text/html')/'; charset=utf-8'
   ∇
   ```

   This covers `html`->`text/html; charset=utf-8`, `css`->`text/css`, `js`->`text/javascript`, `json`->`application/json`. Note: Jarvis only appends `; charset=utf-8` for `text/html` (confirmed Jarvis.aplc line 1767), not for CSS or other types.

4. `RunTests.apls` -- entry-point script following Stark's pattern:
   ```apl
   #!/usr/bin/dyalogscript
   ⎕IO←1
   ⎕SE.(⍎⊃2⎕FIX'/StartupSession.aplf',⍨2⎕NQ#'GetEnvironment' 'DYALOG')
   ⎕SE.Link.Import '#' './Stark/APLSource'
   ⎕SE.Link.Import '#' './APLSource'
   ⎕SE.Link.Import '#.Mocks' './tests/Mocks'
   ⎕SE.Link.Import '#.RunHelper' './tests/RunHelper.apln'
   ⎕SE.Link.Import '#.Unit' './tests/Unit'
   (uPass uFail)←#.RunHelper.Run #.Unit
   ⍝ Integration tests added in Phase 4
   ⎕OFF uFail>0
   ```

5. `Render.apln` -- empty namespace header (`:Namespace Render` / `:EndNamespace`).

6. A single placeholder test in `tests/Unit/`:
   ```apl
   r←Test_Placeholder dummy
   r←1
   ```

### Tests that gate this phase

| Test                | Assertion                                      |
|---------------------|-------------------------------------------------|
| `Test_Placeholder`  | Returns 1. Proves the runner works.             |

### Verify

```bash
dyalogscript RunTests.apls
```

Should print `PASS: Test_Placeholder`, exit 0. Remove the placeholder test once real tests exist.

---

## Phase 2: Render namespace -- Escape and HTML fragment functions

Goal: pure functions that turn data into HTML. No HTTP, no Stark, no side effects. Fully testable in isolation.

### Build

1. `APLSource/Render/Escape.aplf` -- monadic function. Replaces `&`->`&amp;`, `<`->`&lt;`, `>`->`&gt;`, `"`->`&quot;`, `'`->`&#39;` in that order (ampersand first to avoid double-escaping). Returns the modified character vector. Returns `''` for empty input.

2. `APLSource/Render/RespondHTML.aplf` -- dyadic function: `result←html RespondHTML req`. Calls `req.SetContentType 'text/html; charset=utf-8'`. Returns `html`.

3. `APLSource/Render/TodoItem.aplf` -- monadic function accepting a todo namespace (`id`, `title`, `completed`). Returns an `<li>` fragment as a character vector. Uses `Escape` on the title. Applies `class="completed"` when `completed` is 1. Embeds `hx-put`, `hx-delete`, `hx-target`, `hx-swap` attributes with the todo's id.

4. `APLSource/Render/TodoList.aplf` -- monadic function accepting a vector of todo namespaces. Returns the concatenation of `TodoItem` applied to each. Returns empty string for empty input.

### Tests that gate this phase

All in `tests/Unit/`. These test Render functions directly -- no mock request needed (except for `RespondHTML`).

| Test                              | What it verifies                                                                 |
|-----------------------------------|----------------------------------------------------------------------------------|
| `Test_EscapeAmpersand`            | `'a&b'` becomes `'a&amp;b'`                                                     |
| `Test_EscapeLtGt`                 | `'<script>'` becomes `'&lt;script&gt;'`                                          |
| `Test_EscapeQuotes`               | `'"it''s"'` becomes `'&quot;it&#39;s&quot;'`                                     |
| `Test_EscapeCleanString`          | `'hello'` passes through unchanged                                               |
| `Test_EscapeEmpty`                | `''` returns `''`                                                                |
| `Test_EscapeNoDoubleEscape`       | `'&amp;'` becomes `'&amp;amp;'` (each `&` is escaped once, no special-casing)   |
| `Test_TodoItemBasic`              | Incomplete todo produces `<li id="todo-1">` without `class="completed"`          |
| `Test_TodoItemCompleted`          | Completed todo produces `<li id="todo-2" class="completed">`                     |
| `Test_TodoItemEscapedTitle`       | Todo with title `<b>bold</b>` renders `&lt;b&gt;bold&lt;/b&gt;` in the span     |
| `Test_TodoItemHtmxAttrs`          | Output contains `hx-put="/todos/5"`, `hx-delete="/todos/5"`, correct `hx-target` |
| `Test_TodoListEmpty`              | Empty vector produces empty string                                                |
| `Test_TodoListMultiple`           | Vector of 3 todos produces 3 `<li>` elements                                     |
| `Test_RespondHTMLSetsContentType` | After calling `html RespondHTML mockReq`, the mock's `Response.Headers` contains `Content-Type` = `text/html; charset=utf-8` |
| `Test_RespondHTMLReturnsHTML`     | Return value is the same character vector passed as left argument                 |

### Verify

Run the full suite. All phase-2 tests pass. Phase-1 placeholder removed.

---

## Phase 3: Static files -- index.html and style.css

Goal: the front-end assets exist and are well-formed. No server yet, but the files are ready.

### Build

1. `static/index.html`:
   - DOCTYPE, html, head, body structure.
   - `<link rel="stylesheet" href="/style.css">` in head.
   - `<script src="https://unpkg.com/htmx.org@2.0.4"></script>` in head (pin a specific version).
   - A heading (`<h1>Todos</h1>` or similar).
   - A `<form>` with `hx-post="/todos"`, `hx-target="#todo-list"`, `hx-swap="beforeend"`, `hx-on::after-request="this.reset()"`. Contains an `<input type="text" name="title">` and a submit button.
   - A `<ul id="todo-list" hx-get="/todos" hx-trigger="load"></ul>`.

2. `static/style.css`:
   - `.completed span { text-decoration: line-through; opacity: 0.6; }`
   - Cursor pointer on clickable elements.
   - Basic layout (max-width, centring, padding).
   - `.error` styling for error fragments.

### Tests that gate this phase

Unit tests that read the static files from disk with `⎕NGET` and verify structural expectations. These run without a server. The tests resolve file paths relative to the project root (same approach used by `RunTests.apls`).

| Test                           | What it verifies                                                         |
|--------------------------------|--------------------------------------------------------------------------|
| `Test_IndexHtmlExists`         | `⎕NGET` on `static/index.html` succeeds (no file error)                 |
| `Test_IndexHtmlHasHtmxScript`  | Content contains `htmx.org`                                              |
| `Test_IndexHtmlHasForm`        | Content contains `hx-post="/todos"`                                      |
| `Test_IndexHtmlHasTodoList`    | Content contains `id="todo-list"`                                        |
| `Test_IndexHtmlHasStyleLink`   | Content contains `href="/style.css"`                                     |
| `Test_StyleCssExists`          | `⎕NGET` on `static/style.css` succeeds                                  |
| `Test_StyleCssHasCompleted`    | Content contains `.completed`                                            |

### Verify

Full suite green. Static files are well-formed and contain the expected htmx wiring.

---

## Phase 4: TodoApp class -- construction, data model, static file serving

Goal: a running server that serves static files and has the data model in place. No CRUD endpoints yet.

### Build

1. `APLSource/TodoApp.aplc`:

   **Fields:**
   ```apl
   :Field Public Instance router
   :Field Public Instance todos←⍬
   :Field Public Instance nextId←1
   :Field Public Instance staticRoot←''
   ```

   **Constructor** (takes `staticRoot` as argument):
   ```apl
   ∇ make1 root
     :Access Public
     :Implements Constructor
     staticRoot←root,(~(⊃⌽root)∊'/\')/⊃⎕SE.SALTUtils.FS    ⍝ ensure trailing separator
     router←⎕NEW ##.Stark
     router.Handlers←⎕THIS
     router.ThreadMode←0
     router.OnErrorFn←'HandleError'
     '/' router.Get 'ServePage'
     '/style.css' router.Get 'ServeCSS'
   ∇
   ```

   Note: the trailing-separator logic appends `'/'` (or platform separator) only if the path does not already end with one. Alternatively, if `⎕SE.SALTUtils` is not available, use `'/'` directly -- this is Linux-only for this demo.

   Simpler alternative for Linux:
   ```apl
   staticRoot←root,('/'≠⊃⌽root)/'/'
   ```

   **`Start` and `Stop`:**
   ```apl
   ∇ Start port
     :Access Public Instance
     router.Start port
   ∇

   ∇ Stop
     :Access Public Instance
     router.Stop
   ∇
   ```

   **`GetStark`:**
   ```apl
   ∇ r←GetStark
     :Access Public Instance
     r←router
   ∇
   ```

   **`RegisterTestRoutes`** (for OnErrorFn testing, called by test runner only):
   ```apl
   ∇ RegisterTestRoutes
     :Access Public Instance
     '/test/break' router.Get '_BrokenHandler'
   ∇
   ```

   **`_BrokenHandler`** (private, deliberately throws):
   ```apl
   ∇ result←_BrokenHandler req
     :Access Public Instance
     ⎕SIGNAL ⊂('EN' 11)('Message' 'deliberate test error')
   ∇
   ```

   Note: the name starts with `_` so Stark treats it as an internal handler and calls it directly on `Handlers` (the TodoApp instance), which is correct.

2. **Static file handlers on `TodoApp`:**

   ```apl
   ∇ result←ServePage req;path
     :Access Public Instance
     path←staticRoot,'index.html'
     req.SetContentType req.ContentTypeForFile path
     result←⊃⎕NGET path 0
   ∇

   ∇ result←ServeCSS req;path
     :Access Public Instance
     path←staticRoot,'style.css'
     req.SetContentType req.ContentTypeForFile path
     result←⊃⎕NGET path 0
   ∇
   ```

3. **`HandleError`** on `TodoApp` (dyadic -- `OnErrorFn` signature per Stark.aplc line 194):

   ```apl
   ∇ result←err HandleError req
     :Access Public Instance
     result←'<div class="error">Something went wrong</div>' ##.Render.RespondHTML req
   ∇
   ```

   Does not expose `err.Message`, `err.EN`, or any internal details.

4. **`Run.apls`** entry-point script:
   ```apl
   #!/usr/bin/dyalogscript
   ⎕IO←1
   ⎕SE.(⍎⊃2⎕FIX'/StartupSession.aplf',⍨2⎕NQ#'GetEnvironment' 'DYALOG')
   ⎕SE.Link.Import '#' './Stark/APLSource'
   ⎕SE.Link.Import '#' './APLSource'
   staticRoot←⊃1 ⎕NPARTS './static/'
   app←⎕NEW #.TodoApp staticRoot
   app.Start 8080
   ```

   `1 ⎕NPARTS` normalises the relative path to an absolute path with a trailing separator (confirmed in Dyalog docs: `1 ⎕NPARTS` makes pathnames absolute and simplifies them). Since `dyalogscript` sets the working directory to the script's location, `'./static/'` resolves correctly.

### Tests that gate this phase

**Unit tests** (no server needed -- test data model initialisation):

| Test                          | What it verifies                                                         |
|-------------------------------|--------------------------------------------------------------------------|
| `Test_AppInitEmptyTodos`      | After construction, `app.todos` is `⍬` (`0=≢app.todos`)                 |
| `Test_AppInitNextId`          | After construction, `app.nextId` is 1                                    |

Construction in unit tests: `app←⎕NEW #.TodoApp (⊃1 ⎕NPARTS './static/')`. Alternatively, pass an absolute path to `static/` resolved from the test script's location.

**Integration tests** (require a running server):

Update `RunTests.apls` to start `TodoApp` on a test port before integration tests:

```apl
⍝ --- Integration tests ---
port←19877
staticRoot←⊃1 ⎕NPARTS './static/'
app←⎕NEW #.TodoApp staticRoot
app.RegisterTestRoutes                    ⍝ add /test/break for OnErrorFn tests
app.Start port
⎕DL 1                                     ⍝ allow server to initialise
#.Integration.BaseURL←'http://localhost:',(⍕port)
⎕SE.Link.Import '#.Integration' './tests/Integration'
(iPass iFail)←#.RunHelper.Run #.Integration
app.Stop
```

The `⎕DL 1` follows the pattern from Stark's own `RunTests.apls` (line 30).

| Test                               | What it verifies                                                         |
|------------------------------------|--------------------------------------------------------------------------|
| `Test_ServePageStatus`             | `GET /` returns HTTP 200                                                 |
| `Test_ServePageContentType`        | `GET /` response `Content-Type` header contains `text/html`              |
| `Test_ServePageBody`               | `GET /` response body contains `id="todo-list"`                          |
| `Test_ServeCSSStatus`              | `GET /style.css` returns HTTP 200                                        |
| `Test_ServeCSSContentType`         | `GET /style.css` response `Content-Type` header contains `text/css`      |
| `Test_UnknownRouteReturns404`      | `GET /nonexistent` returns HTTP 404                                      |

Integration test example:
```apl
r←Test_ServePageStatus dummy;resp
  resp←#.HttpCommand.Get(BaseURL,'/')
  r←200=resp.HttpStatus
```

### Verify

Full suite green. `dyalogscript Run.apls` starts a server. `curl http://localhost:8080/` returns the HTML page. `curl http://localhost:8080/style.css` returns CSS. Browser can load the page (the todo list will be empty; `GET /todos` will 404 until phase 5).

---

## Phase 5: CRUD endpoints -- list and create

Goal: users can add todos and see the list. The core read/write loop works.

### Build

1. Register routes in `TodoApp` constructor (add after the static routes):
   ```apl
   '/todos' router.Get 'ListTodos'
   '/todos' router.Post 'CreateTodo'
   ```

2. `ListTodos req`:
   ```apl
   ∇ result←ListTodos req
     :Access Public Instance
     result←(##.Render.TodoList todos) ##.Render.RespondHTML req
   ∇
   ```

3. `CreateTodo req`:
   ```apl
   ∇ result←CreateTodo req;title;todo
     :Access Public Instance
     ⍝ Check title field exists
     :If 0=req.Payload.⎕NC⊂'title'
         req.Fail 400
         result←'<div class="error">Title is required</div>' ##.Render.RespondHTML req
         :Return
     :EndIf
     ⍝ Unwrap form-urlencoded value (Jarvis wraps in vector)
     title←⊃req.Payload.title
     ⍝ Trim whitespace and validate non-empty
     title←(∧\' '=title)↓title
     title←(∧\' '=⌽title)↓⍨⍥≢title   ⍝ or: title←' '(~∘⊣⌿⍨∨⍀∘⊢∧⊢∨∧⍀∘⊢)title for a more idiomatic trim
     :If 0=≢title
         req.Fail 400
         result←'<div class="error">Title must not be empty</div>' ##.Render.RespondHTML req
         :Return
     :EndIf
     ⍝ Create todo
     todo←⎕NS ''
     todo.(id title completed)←nextId title 0
     nextId+←1
     todos,←⊂todo
     req.StatusCode←201
     result←(##.Render.TodoItem todo) ##.Render.RespondHTML req
   ∇
   ```

   Note on trim: the exact APL idiom for trimming is left to the implementer, but the semantics are: strip leading and trailing spaces. The tests below verify the behaviour.

### Tests that gate this phase

**Unit tests** (via MockRequest, no server):

Setup pattern for CreateTodo unit tests:
```apl
app←⎕NEW #.TodoApp (⊃1 ⎕NPARTS './static/')
req←⎕NEW #.Mocks.MockRequest ('POST' '/todos')
req.Payload←⎕NS ''
req.Payload.title←,⊂'Buy milk'     ⍝ enclosed, as Jarvis does for form data
result←app.CreateTodo req
```

| Test                              | What it verifies                                                                  |
|-----------------------------------|-----------------------------------------------------------------------------------|
| `Test_CreateTodoAddsItem`         | After calling `CreateTodo` with a valid payload, `app.todos` has 1 element        |
| `Test_CreateTodoReturnsLi`        | Return value contains `<li`                                                       |
| `Test_CreateTodoSetsId`           | The created todo has `id=1`; creating a second gives `id=2`                       |
| `Test_CreateTodoStatus201`        | `req.StatusCode` is 201 after creation                                            |
| `Test_CreateTodoMissingTitle`     | Payload with no `title` field: `req.Response.Status` is 400                       |
| `Test_CreateTodoEmptyTitle`       | Payload with `title←,⊂''`: `req.Response.Status` is 400                          |
| `Test_CreateTodoWhitespaceTitle`  | Payload with `title←,⊂'   '` (spaces only): `req.Response.Status` is 400         |
| `Test_ListTodosEmpty`             | With no todos, `ListTodos` returns empty string via `RespondHTML`                 |
| `Test_ListTodosAfterCreate`       | After creating 2 todos, `ListTodos` return contains both `<li` elements           |

**Integration tests** (over HTTP):

HttpCommand auto-detects `application/x-www-form-urlencoded` when the body is a simple character vector that does not look like JSON (HttpCommand.aplc lines 550-554). No explicit content-type argument needed:
```apl
resp←#.HttpCommand.Do 'POST' (BaseURL,'/todos') 'title=Buy milk'
```

| Test                              | What it verifies                                                                  |
|-----------------------------------|-----------------------------------------------------------------------------------|
| `Test_PostTodoReturns201`         | `POST /todos` with `title=Buy milk` returns HTTP 201                              |
| `Test_PostTodoReturnsFragment`    | Response body contains `<li` and `Buy milk`                                       |
| `Test_PostTodoContentType`        | Response content-type contains `text/html`                                        |
| `Test_GetTodosAfterPost`          | After POST, `GET /todos` returns fragment containing the created todo             |
| `Test_PostTodoNoTitle`            | `POST /todos` with empty body returns HTTP 400                                    |
| `Test_PostTodoEmptyTitle`         | `POST /todos` with `title=` (empty value) returns HTTP 400                        |
| `Test_PostTodoXSSEscaped`         | `POST /todos` with `title=<script>alert(1)</script>`, then `GET /todos` -- response contains `&lt;script&gt;`, not `<script>` |

### Verify

Full suite green. In a browser, the page loads, the form submits, new todos appear in the list without page reload.

---

## Phase 6: CRUD endpoints -- toggle and delete

Goal: full CRUD cycle. Users can mark todos complete/incomplete and delete them.

### Build

1. Register routes in `TodoApp` constructor (add after list/create routes):
   ```apl
   '/todos/{id}' router.Put 'ToggleTodo'
   '/todos/{id}' router.Delete 'DeleteTodo'
   ```

2. **`FindTodo`** -- a private helper that factors out the id-parsing and lookup pattern:
   ```apl
   ∇ idx←FindTodo req;valid;values;id;mask
     :Access Private Instance
     (valid values)←⎕VFI req.PathParams.id
     :If (1≠≢valid)∨(~⊃valid)
         req.Fail 400
         idx←¯1
         :Return
     :EndIf
     id←⊃values
     mask←todos.id=id
     :If ~∨/mask
         req.Fail 404
         idx←¯1
         :Return
     :EndIf
     idx←mask⍳1
   ∇
   ```

   Returns `¯1` on any error (invalid id or not found), with `req.Fail` already called. Returns the positive index on success.

3. **`ToggleTodo req`:**
   ```apl
   ∇ result←ToggleTodo req;idx;todo
     :Access Public Instance
     idx←FindTodo req
     :If ¯1=idx
         result←'<div class="error">Not found</div>' ##.Render.RespondHTML req
         :Return
     :EndIf
     todo←idx⊃todos
     todo.completed←~todo.completed
     result←(##.Render.TodoItem todo) ##.Render.RespondHTML req
   ∇
   ```

4. **`DeleteTodo req`:**
   ```apl
   ∇ result←DeleteTodo req;idx
     :Access Public Instance
     idx←FindTodo req
     :If ¯1=idx
         result←'<div class="error">Not found</div>' ##.Render.RespondHTML req
         :Return
     :EndIf
     todos←todos~⊂idx⊃todos
     result←'' ##.Render.RespondHTML req
   ∇
   ```

   Note on deletion: `todos~⊂idx⊃todos` removes by value. Since each todo is a distinct namespace reference, this is unambiguous. Alternatively, use `todos←(⍳≢todos)≠idx)⌿todos` for index-based removal.

### Tests that gate this phase

**Unit tests** (via MockRequest):

Setup pattern:
```apl
app←⎕NEW #.TodoApp (⊃1 ⎕NPARTS './static/')
⍝ Create a todo first
req←⎕NEW #.Mocks.MockRequest ('POST' '/todos')
req.Payload←⎕NS '' ⋄ req.Payload.title←,⊂'Test item'
{}app.CreateTodo req
⍝ Now toggle it
req←⎕NEW #.Mocks.MockRequest ('PUT' '/todos/1')
req.PathParams←⎕NS '' ⋄ req.PathParams.id←'1'
result←app.ToggleTodo req
```

| Test                                | What it verifies                                                                 |
|-------------------------------------|----------------------------------------------------------------------------------|
| `Test_ToggleTodoFlipsCompleted`     | After toggle on an incomplete todo, `completed` is 1                             |
| `Test_ToggleTodoFlipsBack`          | Toggle twice returns to `completed=0`                                            |
| `Test_ToggleTodoReturnsLi`          | Return value contains `class="completed"` after toggling to complete             |
| `Test_ToggleTodoInvalidId`          | Path param `id='abc'`: `req.Response.Status` is 400                              |
| `Test_ToggleTodoMultiTokenId`       | Path param `id='1 2'`: `req.Response.Status` is 400                              |
| `Test_ToggleTodoNotFound`           | Path param `id='999'`: `req.Response.Status` is 404                              |
| `Test_DeleteTodoRemovesItem`        | After delete, `app.todos` length decreases by 1                                  |
| `Test_DeleteTodoReturnsEmpty`       | Return value (the HTML part) is empty string                                     |
| `Test_DeleteTodoInvalidId`          | Path param `id='abc'`: `req.Response.Status` is 400                              |
| `Test_DeleteTodoNotFound`           | Path param `id='999'`: `req.Response.Status` is 404                              |
| `Test_DeleteTodoIdNotReused`        | After deleting todo 1 and creating a new todo, the new todo's id is not 1        |

**Integration tests** (over HTTP):

| Test                                | What it verifies                                                                 |
|-------------------------------------|----------------------------------------------------------------------------------|
| `Test_PutTodoToggles`               | POST a todo, PUT it, response contains `class="completed"`                       |
| `Test_PutTodoToggleBack`            | PUT the same todo again, response does not contain `class="completed"`           |
| `Test_PutTodoInvalidId`             | `PUT /todos/abc` returns HTTP 400                                                |
| `Test_PutTodoNotFound`              | `PUT /todos/99999` returns HTTP 404                                              |
| `Test_DeleteTodoReturns200`         | POST a todo, DELETE it, returns HTTP 200                                         |
| `Test_DeleteTodoActuallyRemoves`    | After DELETE, `GET /todos` no longer contains the deleted item                   |
| `Test_DeleteTodoInvalidId`          | `DELETE /todos/abc` returns HTTP 400                                             |
| `Test_DeleteTodoNotFound`           | `DELETE /todos/99999` returns HTTP 404                                           |

### Verify

Full suite green. In a browser, the complete CRUD flow works: add, toggle, delete, all via htmx without page reloads.

---

## Phase 7: Error handling and hardening

Goal: the `OnErrorFn` handler works, content-types are correct everywhere, and edge cases are covered.

### Build

1. Verify that `HandleError` is correctly wired (already done in phase 4 constructor, tested now).

2. Review every handler to confirm:
   - API handlers always call `RespondHTML` as the last step (content-type safety net).
   - Static file handlers always call `req.SetContentType` via `ContentTypeForFile`.
   - Error paths (`req.Fail 400/404`) return HTML error fragments via `RespondHTML`.

3. Missing static file errors (`⎕NGET` on absent `index.html` or `style.css`) are deployment errors. They will throw, be caught by `OnErrorFn`, and produce a 500 with a generic HTML body. No explicit `:Trap` needed in the static file handlers.

### Tests that gate this phase

**Unit tests:**

| Test                                  | What it verifies                                                             |
|---------------------------------------|------------------------------------------------------------------------------|
| `Test_HandleErrorReturnsHTML`         | Call `err HandleError mockReq` directly. `err` is a namespace with `EN←11`, `EM←'DOMAIN ERROR'`, `Message←'test'`. Verify the result is a character vector and `mockReq`'s content-type is `text/html; charset=utf-8`. |
| `Test_HandleErrorGenericMessage`      | Same setup. The returned HTML does not contain `'test'` (the `err.Message` value). |

**Integration tests:**

The `/test/break` route was registered by calling `app.RegisterTestRoutes` in the test runner setup (Phase 4 integration test setup). The `_BrokenHandler` method on `TodoApp` signals EN 11. Stark's `OnErrorFn` mechanism catches this, calls `req.Fail 500`, then invokes `err HandleError req`.

| Test                                  | What it verifies                                                             |
|---------------------------------------|------------------------------------------------------------------------------|
| `Test_OnErrorFnReturns500`            | `GET /test/break` returns HTTP 500                                           |
| `Test_OnErrorFnReturnsHTML`           | Same request: content-type contains `text/html`, body contains `class="error"` |
| `Test_OnErrorFnNoInfoLeak`            | Same request: body does not contain `deliberate test error` or `DOMAIN ERROR` |
| `Test_AllEndpointsCorrectContentType` | For `GET /`, `GET /style.css`, `GET /todos`, `POST /todos` (with valid body), `PUT /todos/{id}` (after creating a todo), `DELETE /todos/{id}` -- verify the content-type is never `application/json` |

### Verify

Full suite green. No endpoint returns `application/json`. Unexpected errors produce a clean 500 with an HTML body.

---

## Phase 8: End-to-end integration and the full test runner

Goal: a single `RunTests.apls` that runs all unit and integration tests, with clean startup/teardown. The application is shippable.

### Build

1. Finalise `RunTests.apls`:
   ```apl
   #!/usr/bin/dyalogscript
   ⎕IO←1
   ⎕SE.(⍎⊃2⎕FIX'/StartupSession.aplf',⍨2⎕NQ#'GetEnvironment' 'DYALOG')

   ⍝ Import framework and app
   ⎕SE.Link.Import '#' './Stark/APLSource'
   ⎕SE.Link.Import '#' './APLSource'

   ⍝ Import test infrastructure
   ⎕SE.Link.Import '#.Mocks' './tests/Mocks'
   ⎕SE.Link.Import '#.RunHelper' './tests/RunHelper.apln'
   ⎕SE.Link.Import '#.HttpCommand' './Stark/Tests/HttpCommand.aplc'

   ⍝ --- Unit tests ---
   ⎕SE.Link.Import '#.Unit' './tests/Unit'
   ⎕←'=== Unit Tests ==='
   (uPass uFail)←#.RunHelper.Run #.Unit

   ⍝ --- Integration tests ---
   port←19877
   staticRoot←⊃1 ⎕NPARTS './static/'
   app←⎕NEW #.TodoApp staticRoot
   app.RegisterTestRoutes
   app.Start port
   ⎕DL 1

   #.Integration.BaseURL←'http://localhost:',(⍕port)
   ⎕SE.Link.Import '#.Integration' './tests/Integration'
   ⎕←'=== Integration Tests ==='
   (iPass iFail)←#.RunHelper.Run #.Integration

   app.Stop

   ⍝ --- Summary ---
   ⎕←''
   ⎕←'=== Summary ==='
   ⎕←'Unit:       ',(⍕uPass),' passed, ',(⍕uFail),' failed'
   ⎕←'Integration: ',(⍕iPass),' passed, ',(⍕iFail),' failed'
   ⎕OFF(uFail+iFail)>0
   ```

2. Verify `Run.apls` works as the production entry point (manual check -- start server, open browser, exercise all CRUD operations).

3. Cleanup review: remove any placeholder tests, debug `⎕←` statements, or temporary code. Verify no `.skip` tests exist without documentation.

### Tests that gate this phase

No new tests. The gate is: **all tests from phases 2-7 pass in a single run of `RunTests.apls`**, and the exit code is 0.

### Verify

```bash
dyalogscript RunTests.apls
```

All tests pass. The application starts with `dyalogscript Run.apls` and is usable in a browser.

---

## Phase summary

| Phase | What it delivers                           | Unit tests | Integration tests |
|-------|--------------------------------------------|------------|-------------------|
| 1     | Scaffolding and test runner                | 1          | 0                 |
| 2     | Render namespace (Escape, TodoItem, etc.)  | 14         | 0                 |
| 3     | Static files (index.html, style.css)       | 7          | 0                 |
| 4     | TodoApp class, static serving, OnErrorFn   | 2          | 6                 |
| 5     | List and create endpoints                  | 9          | 7                 |
| 6     | Toggle and delete endpoints                | 11         | 8                 |
| 7     | Error handling hardening                   | 2          | 4                 |
| 8     | Final integration, cleanup                 | 0          | 0                 |
| **Total** |                                        | **46**     | **25**            |

## Error handling summary

| Error condition              | Where handled                   | HTTP status | Response body                                    |
|------------------------------|---------------------------------|-------------|--------------------------------------------------|
| Missing/empty/whitespace title on POST | `CreateTodo`            | 400         | `<div class="error">Title is required</div>` (or similar) |
| Non-numeric id on PUT/DELETE | `FindTodo`                      | 400         | `<div class="error">Invalid id</div>`            |
| Multi-token id (e.g. `1 2`)  | `FindTodo`                     | 400         | `<div class="error">Invalid id</div>`            |
| Non-existent id on PUT/DELETE | `FindTodo`                     | 404         | `<div class="error">Not found</div>`             |
| Unknown route                | Stark `_Dispatch`               | 404         | JSON (Stark default, not ours)                   |
| Unhandled exception          | `HandleError` via `OnErrorFn`   | 500         | `<div class="error">Something went wrong</div>`  |
| Missing static file on disk  | `HandleError` via `OnErrorFn`   | 500         | `<div class="error">Something went wrong</div>`  |

## Direct navigation to fragment endpoints

If a user navigates directly to `/todos` in the browser (rather than via htmx), they receive a bare HTML fragment without page chrome. This is standard htmx behaviour and acceptable for a demo. A production application could check the `HX-Request` header and return a full page for non-htmx requests; noted as a future enhancement, not a current requirement.

## Revision log

| Date       | Revision | Notes                                                    |
|------------|----------|----------------------------------------------------------|
| 2026-03-27 | 1        | Initial draft derived from architecture.md revision 3    |
| 2026-03-27 | 2        | Revised per adversarial review (docs/reviews/implementation.md). Key changes: full MockRequest spec with SetContentType and ContentTypeForFile methods; fixed ⎕VFI validation for multi-token input; staticRoot passed as constructor argument (not self-resolved); todos/nextId made Public fields; FindTodo returns ¯1 not ⍬; fixed ⎕NC check (0 not 9.1); all error paths return HTML fragments via RespondHTML; specified /test/break registration via RegisterTestRoutes; verified HttpCommand form-urlencoded auto-detection; added ⎕DL 1 after server start; added whitespace-only title test; added XSS integration test; added multi-token id test; added direct-navigation note; concrete APL code for all handlers. |
