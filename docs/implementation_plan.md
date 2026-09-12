# Implementation Plan: US-03 View Product Backlog Feature

This plan details the implementation for **US-03: View Product Backlog**, specifically assigned to **Chloe Lai (Product Owner)**. It translates the client requirements and team inception standards into an industry-grade, clean Django web application matching the provided UI design.

---

## 1. Actual Client Requirements (Synthesis from Client Meetings)

Based on the client interviews and Project Inception document:
1. **Backlog Display**:
   - The Product Backlog must display all active project tasks (stories and bugs).
   - Each backlog item must show its **Task Name / Title**, associated **Tags** (e.g., `UI, UX`, `Front-end`, `Back-end`, `API`, `Database`, `Testing`), **Priority Badge** (with strict color rules: `Low` = Green, `Medium`/`Important` = Yellow/Orange, `Urgent` = Red), and **Story Points** (whole numbers 0–10).
2. **Sprints Sidebar & Context**:
   - Sidebar displays all sprints with statuses (`Active`, `Completed`, `Planning`).
   - Strict rule: **Only one active sprint is allowed at a time**.
   - Tasks in the backlog can be planned and assigned into the active sprint.
3. **Filtering & Sorting Capabilities**:
   - **Tag Filtering**: Filter backlog tasks dynamically by one or more tags.
   - **Priority & Date Sorting**:
     - *Lowest to Urgent priorities*
     - *Urgent to Lowest priorities*
     - *Most recent to oldest*
     - *Oldest to most recent*
4. **View Toggling**:
   - Support toggling between **List View** (structured tabular/row layout per mockup) and **Card View** (Kanban style).
5. **Security & Access Control**:
   - Multi-role readiness (Admin vs Team Member), ensuring soft-deleted tasks are hidden from general view.

---

## 2. Webpage Visual Architecture & Wireframe Layout

The layout will strictly reproduce the mockup provided by Chloe:

```
+---------------------------------------------------------------------------------------------------+
|  [Logo] AgileFlow  |  Project: Product 1 Backlog                                    (User: Chloe) |
+---------------------------------------------------------------------------------------------------+
|  SPRINTS SIDEBAR (Left)           |  PRODUCT 1 BACKLOG (Main Workspace)                          |
|                                   |                                                               |
|  Sprints                          |  Product 1 Backlog          Sort by: [Urgent to lowest v]    |
|  Click to show more               |                             [Filter task (Tags) v]  (List/Card)|
|                                   +---------------------------------------------------------------+
|  +-----------------------------+  |  Task name         | Tags        | Priority   | Story point    |
|  | Sprint 1      [Completed v] |  |  +---------------+ +-----------+ +----------+ +-------------+  |
|  +-----------------------------+  |  | Task 1: UI UX | | UI, UX    | | Low      | |     3       |  |
|  | Sprint 2      [Completed v] |  |  | Setup Figma   | |           | | (Green)  | |   (Dark)    |  |
|  +-----------------------------+  |  +---------------+ +-----------+ +----------+ +-------------+  |
|  | Sprint 3      [Active    v] |  |  | Task 2: Auth  | | Front-end | | Urgent   | |    10       |  |
|  +-----------------------------+  |  | Login Screen  | |           | | (Red)    | |   (Dark)    |  |
|                                   |  +---------------+ +-----------+ +----------+ +-------------+  |
|  [ + Add new sprint ]             |                                                               |
|  * Note: Only 1 active sprint     |  [ + Create new task ]                                        |
+-----------------------------------+---------------------------------------------------------------+
```

---

## 3. Industry Standard Architecture & Standards

### A. Backend Architecture (Django 6.1 / Python)
* **Design Pattern**: Django Model-View-Template (MVT) with separation of concerns.
* **Coding Standards (from Project Inception §11.1)**:
  * Python/Django: `snake_case` for variables, methods, and functions; `PascalCase` for model and class names.
  * Explicit query optimization using `prefetch_related('tags')` and `select_related('assignee')`.
  * Safe database interactions via Django ORM (no hardcoded raw SQL).

### B. Database Design (PostgreSQL compatible, SQLite local dev)
* **`Tag` Model**: `name` (unique), `color_class`.
* **`Sprint` Model**: `name`, `goal`, `start_date`, `end_date`, `status` (`planning`, `active`, `completed`).
* **`Task` Model**:
  * `title`, `description`, `acceptance_criteria`
  * `item_type`: `'story'`, `'bug'` (default: `'story'`)
  * `story_points`: `IntegerField` (0–10)
  * `priority`: `'low'`, `'medium'`, `'important'`, `'urgent'`
  * `stage`: `'planning'`, `'development'`, `'testing'`, `'integration'`
  * `status`: `'not_started'`, `'in_progress'`, `'completed'`
  * `tags`: `ManyToManyField(Tag)`
  * `sprint`: `ForeignKey(Sprint, null=True, blank=True)`
  * `is_deleted`: `BooleanField(default=False)` (soft delete support)
  * `created_at`, `updated_at`

### C. Frontend Architecture (HTML5, Bootstrap 5, Modern CSS, Vanilla JS)
* **Design Aesthetic**: Modern, responsive layout matching the screenshot; clear color hierarchy for priorities (`badge-priority-low`, `badge-priority-medium`, `badge-priority-important`, `badge-priority-urgent`), dark badges for tags, and boxed story point indicators.
* **JavaScript**: Pure Vanilla JS for instant view switching (List vs Card) and responsive interactions, using `const`/`let` and `camelCase`.

---

## 4. Git Policy Compliance (from Project Inception §6 & §11.1.8)
* **Branch**: `feature/FIT-US03-view-product-backlog`
* **Commit Standard**: Conventional commits format (e.g., `feat: implement product backlog list and card views with tag filtering and priority sorting`).

---

## 5. Proposed Code & File Changes

### Component: Backlog Application

#### [NEW] [models.py](file:///c:/Users/user/Documents/FIT%202101/backlog/models.py)
* Define `Tag`, `Sprint`, and `Task` models with comprehensive fields and validations.

#### [NEW] [views.py](file:///c:/Users/user/Documents/FIT%202101/backlog/views.py)
* Implement `product_backlog` view with filtering (tags, status, priority), sorting (priority asc/desc, date asc/desc), and metric aggregates.

#### [NEW] [urls.py](file:///c:/Users/user/Documents/FIT%202101/backlog/urls.py)
* Route mapping for the backlog dashboard and views.

#### [NEW] [templates/base.html](file:///c:/Users/user/Documents/FIT%202101/templates/base.html)
* Master layout with Bootstrap 5 CDN, navigation header, and responsive container.

#### [NEW] [templates/backlog/product_backlog.html](file:///c:/Users/user/Documents/FIT%202101/templates/backlog/product_backlog.html)
* High-fidelity template implementing the exact layout from the wireframe screenshot:
  * Left-hand Sprint sidebar with status pills (`Completed`, `Active`).
  * Right-hand Product Backlog table/row layout with custom badge styles.
  * Tag filter dropdown & interactive sort dropdown.
  * List/Card toggle switcher.

#### [NEW] [static/css/styles.css](file:///c:/Users/user/Documents/FIT%202101/static/css/styles.css)
* Custom CSS variables, priority color indicators, and modern card styling.

#### [NEW] [management/commands/seed_backlog.py](file:///c:/Users/user/Documents/FIT%202101/backlog/management/commands/seed_backlog.py)
* Automated sample data seeder loading Sprint 1 tasks and realistic stories for testing.

---

## 6. Verification Plan

### Automated Verification:
* Run Django system check: `python manage.py check`
* Run database migrations: `python manage.py makemigrations && python manage.py migrate`
* Run Django unit tests: `python manage.py test backlog`

### Manual & Visual Verification:
* Launch local dev server: `python manage.py runserver 8000`
* Verify that:
  1. Product backlog list displays all tasks with Task Name, Tags, Priority color, and Story Points box.
  2. Sprints sidebar shows Sprints with correct Active/Completed status badges.
  3. Sorting works across all 4 options (Lowest to Urgent, Urgent to Lowest, Recent to Oldest, Oldest to Recent).
  4. Tag filtering correctly filters items.
  5. List View and Card View toggle smoothly.
  6. The layout adapts cleanly to desktop and mobile viewports.
