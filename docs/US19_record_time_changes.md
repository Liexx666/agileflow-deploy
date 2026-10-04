# US-19 Record Time Worked on a Sprint Task：实现与代码改动说明

实现分支：`sprint2-yaoxing`。基于目前已合并的 Ethan 前端实现。

## 1. 实现思路

一次工作 = 一条 TaskWorkSession，保存 task、user、started_at、ended_at。
这样同一任务可以有多段记录；任务重新分配后，不同成员的记录仍独立归属于原记录人。
现有模型只有单个 assignee，因此本次沿用单负责人结构；同一时刻仅该负责人且属于 Sprint 团队的用户可以记录。

处理顺序：四个日期/时间输入 → Form 检查格式和前后顺序 → 服务检查权限与状态 → 检查重叠 → 在同一事务里保存记录和总工时 → 返回详情页。

时长由后端计算，用户无法用 duration 或 user_id 参数伪造自己的时长/记录人。
工时开始和结束使用项目时区 Asia/Kuala_Lumpur，数据库使用 Django 的时区支持。

## 2. 关键规则的直觉

重叠条件为：旧开始 < 新结束 AND 旧结束 > 新开始。
例如 09:00–10:00 与 09:30–10:30 会重叠；09:00–10:00 与 10:00–11:00 相邻，允许保存。
查询限定同一个 user，但不限定 task，所以跨不同任务也不能重叠。
编辑时排除被编辑记录本身，避免不改变时间时错误地与自己重叠。

只有 Sprint 的 team_members 中且等于 task.assignee 的用户可以记录或编辑。
前端隐藏按钮提升可用性；服务端再次验证，防止通过手写请求绕过。
Sprint 非 active，或者任务 completed 时，新增和编辑都被阻止；已有个人历史仍可查看。
工时记录保存在独立表中，不写入共享 TaskHistory，避免其他成员从通用 History 中看到个人工时明细。

任务总工时继续使用 accumulated_hours，保留其他已有功能的读取方式。
新记录先以完整时间差相加，最后统一舍入为两位小数，避免多条一分钟记录分别舍入导致总数错误。
旧数据库只有累计小时数，缺少对应的人和起止时间；保留这一历史累计值，再加上本次记录的时长，不虚构历史个人记录。

服务使用事务以及用户、任务和 Sprint 行锁，在支持行锁的数据库上串行处理同一用户的并发提交。
SQLite 测试不能证明 PostgreSQL 下的并发行为；本次未连接或迁移云端 PostgreSQL。
参考：[Django 行锁文档](https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update)、[Django 时区文档](https://docs.djangoproject.com/en/5.2/topics/i18n/timezones/)。

## 3. 验收标准对应

| AC | 实现 |
|---|---|
| 1 | 后端同时检查 task.assignee 和 sprint.team_members；管理员不绕过这条规则。 |
| 2–3 | 现有两个弹窗都接入 Start Date/Time 与 End Date/Time。 |
| 4 | duration = ended_at - started_at，由后端计算。 |
| 5 | TaskWorkSession 是独立记录表，支持多段工作。 |
| 6 | 每次新增/编辑同步 accumulated_hours。 |
| 7 | 每条记录关联记录用户，不依赖当前负责人来推断过去是谁记录的。 |
| 8 | 看板三列的任务卡片和看板数据 API 提供总工时。 |
| 9 | Product Backlog 不显示工时；没有 Sprint 的任务详情也不显示工时面板。 |
| 10 | 同一用户跨所有任务的时间段都检查重叠；允许首尾相接。 |
| 11 | 已完成任务不能新增和编辑；已有历史可读。 |
| 12 | 仅 active Sprint 允许记录/编辑。 |
| 13 | 详情页查询 work_sessions.filter(user=request.user)，编辑请求也验证记录归属。 |
| 14 | 原生 type=date 和 type=time 输入保留，并配上日历/时钟标签图标。选择器外观由浏览器决定。 |

## 4. 验证和本地数据库

- US-19 新增 33 项测试通过。
- accounts 与 backlog 合计 147 项测试全部通过。
- makemigrations --check --dry-run：No changes detected。
- Django system check：无错误；JavaScript 语法检查与 Git diff 空白检查通过。
- 自动化测试使用隔离的内存 SQLite。
- 浏览器测试使用独立临时数据库：记录 09:00–10:30，编辑为 09:00–11:00，再添加 11:00–12:15；个人历史和看板均显示 3h 15m。重叠提交被拒绝，错误弹窗保留输入。
- 本地 db.sqlite3 已应用 backlog 0009 及它依赖的前端迁移；原有 5 个任务、3 个 Sprint 的数量保留，迁移前只有至多一个 active Sprint，因此没有触发旧迁移中修改重复 active Sprint 状态的分支。
- 迁移前备份：db.before-us19-20260930-215439.sqlite3，位于项目根目录，Git 会忽略 SQLite 文件。
- 未做 Git commit 或 push。

## 5. 本地运行

本次发现 `.venv/Scripts/python.exe` 指向已不存在的 Python313，无法启动。
测试使用可用的捆绑 Python312，加载项目原有 `.venv/Lib/site-packages`，没有更改 requirements 或重建原有虚拟环境。
你可以在项目根目录的 PowerShell 临时这样启动：

```powershell
$env:PYTHONPATH = "$PWD\.venv\Lib\site-packages"
& "C:\Users\liexx\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" manage.py runserver
```

这使用的是当前本地配置。完成后，可在同一终端删除本次设置的 PYTHONPATH：

```powershell
Remove-Item Env:PYTHONPATH
```

本地迁移已完成。其他同事拉取代码后，需要在他们的正常 Django 环境执行 `python manage.py migrate`。
运行界面时，以被分配该任务且属于 Sprint 团队的账号登录，Sprint 设为 Active，任务不能为 Completed。

## 6. 性能与取舍

每次提交在数据库中聚合该任务的已有 n 段记录，耗时 O(n)，结果只传回一个总时间，不把所有明细加载到 Python。
重叠查询使用 user/start 索引缩小到当前用户的候选记录，最坏仍需检查该用户的 m 段记录；并非保证 O(1)。
看板直接读取已经同步的 accumulated_hours，因此没有为每张卡片再次查询所有工时记录，适合目前的小组项目。

## 7. 逐文件原代码与新代码

下面是本次改动的完整差异。`-` 开头是删除的旧代码，`+` 开头是新增的代码。
新增文件的内容全部在 `+` 行中；不用复制 `+` 本身。
这些修改已经写进你的分支工作目录，本说明用于理解和审阅。

### backlog/models.py

新增 TaskWorkSession，每段工作分别关联任务和成员，保存开始/结束时间；duration 和 duration_label 自动从时间戳计算；数据库拒绝非正时长。

```diff
diff --git a/backlog/models.py b/backlog/models.py
index 453ec7e..d31e916 100644
--- a/backlog/models.py
+++ b/backlog/models.py
@@ -224,6 +224,40 @@ class TaskHistory(models.Model):
     def __str__(self):
         return f"{self.timestamp:%Y-%m-%d %H:%M} — {self.description}"
 
+
+class TaskWorkSession(models.Model):
+    """One member's work interval; duration is derived from its timestamps."""
+
+    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="work_sessions")
+    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="work_sessions")
+    started_at = models.DateTimeField()
+    ended_at = models.DateTimeField()
+    created_at = models.DateTimeField(auto_now_add=True)
+    updated_at = models.DateTimeField(auto_now=True)
+
+    class Meta:
+        ordering = ["-started_at", "-pk"]
+        indexes = [models.Index(fields=["user", "started_at"], name="work_session_user_start")]
+        constraints = [
+            models.CheckConstraint(
+                condition=Q(ended_at__gt=models.F("started_at")),
+                name="work_session_positive_duration",
+            ),
+        ]
+
+    @property
+    def duration(self):
+        return self.ended_at - self.started_at
+
+    @property
+    def duration_label(self):
+        hours, minutes = divmod(int(self.duration.total_seconds()) // 60, 60)
+        return f"{hours}h {minutes:02d}m"
+
+    def __str__(self):
+        return f"{self.user} — {self.task} ({self.duration_label})"
+
+
 class SprintBoardPreference(models.Model):
     """Stores each user's preferred layout for an individual Sprint board."""
 
```

### backlog/migrations/0009_task_work_session.py

新增工时表、用户/开始时间索引、结束时间必须晚于开始时间的数据库约束。迁移依赖现有两个分支合并后的 0008。

```diff
diff --git a/backlog/migrations/0009_task_work_session.py b/backlog/migrations/0009_task_work_session.py
new file mode 100644
--- /dev/null
+++ b/backlog/migrations/0009_task_work_session.py
@@ -0,0 +1,33 @@
+# Generated by Django 5.2.17 on 2026-09-30 13:51
+
+import django.db.models.deletion
+from django.conf import settings
+from django.db import migrations, models
+
+
+class Migration(migrations.Migration):
+
+    dependencies = [
+        ('backlog', '0008_merge_20260927_1805'),
+        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
+    ]
+
+    operations = [
+        migrations.CreateModel(
+            name='TaskWorkSession',
+            fields=[
+                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
+                ('started_at', models.DateTimeField()),
+                ('ended_at', models.DateTimeField()),
+                ('created_at', models.DateTimeField(auto_now_add=True)),
+                ('updated_at', models.DateTimeField(auto_now=True)),
+                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='work_sessions', to='backlog.task')),
+                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='work_sessions', to=settings.AUTH_USER_MODEL)),
+            ],
+            options={
+                'ordering': ['-started_at', '-pk'],
+                'indexes': [models.Index(fields=['user', 'started_at'], name='work_session_user_start')],
+                'constraints': [models.CheckConstraint(condition=models.Q(('ended_at__gt', models.F('started_at'))), name='work_session_positive_duration')],
+            },
+        ),
+    ]
```

### backlog/sprint_forms.py

新增 WorkSessionForm，接收现有前端的四个日期/时间字段，转换成项目时区的 aware datetime；拒绝缺失、非法、倒序和相同时间。

```diff
diff --git a/backlog/sprint_forms.py b/backlog/sprint_forms.py
index e418acf..66e177f 100644
--- a/backlog/sprint_forms.py
+++ b/backlog/sprint_forms.py
@@ -1,4 +1,5 @@
 from django import forms
+from datetime import datetime
 
 from .models import Sprint, SprintBoardPreference, Task
 
@@ -30,4 +31,33 @@ class SprintBoardViewForm(forms.Form):
 class SprintStatusForm(forms.Form):
     status = forms.ChoiceField(
         choices=Sprint.STATUS_CHOICES,
-    )
\ No newline at end of file
+    )
+
+
+class WorkSessionForm(forms.Form):
+    """Parse the existing separate calendar/clock inputs in the current timezone."""
+
+    start_date = forms.DateField(widget=forms.DateInput(
+        format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"},
+    ))
+    start_time = forms.TimeField(input_formats=["%H:%M"], widget=forms.TimeInput(
+        format="%H:%M", attrs={"type": "time", "class": "form-control", "step": "60"},
+    ))
+    end_date = forms.DateField(widget=forms.DateInput(
+        format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"},
+    ))
+    end_time = forms.TimeField(input_formats=["%H:%M"], widget=forms.TimeInput(
+        format="%H:%M", attrs={"type": "time", "class": "form-control", "step": "60"},
+    ))
+
+    def clean(self):
+        cleaned = super().clean()
+        for name in ("start", "end"):
+            date, time = cleaned.get(f"{name}_date"), cleaned.get(f"{name}_time")
+            if date is not None and time is not None:
+                # DateTimeField also rejects ambiguous/nonexistent local times in DST zones.
+                cleaned[f"{name}ed_at"] = forms.DateTimeField().clean(datetime.combine(date, time))
+        if "started_at" in cleaned and "ended_at" in cleaned:
+            if cleaned["ended_at"] <= cleaned["started_at"]:
+                raise forms.ValidationError("End date and time must be after start date and time.")
+        return cleaned
```

### backlog/sprint_services.py

新增可用性检查与 save_work_session 服务；事务内校验任务分配、Sprint 成员、活跃状态、完成状态和跨任务重叠；保存或修改个人记录并同步总工时。

```diff
diff --git a/backlog/sprint_services.py b/backlog/sprint_services.py
index b993946..6914573 100644
--- a/backlog/sprint_services.py
+++ b/backlog/sprint_services.py
@@ -1,11 +1,17 @@
-from django.core.exceptions import ValidationError
+from datetime import timedelta
+from decimal import Decimal, ROUND_HALF_UP
+
+from django.contrib.auth import get_user_model
+from django.core.exceptions import PermissionDenied, ValidationError
 from django.db import IntegrityError, transaction
+from django.db.models import DurationField, ExpressionWrapper, F, Sum
 
 from .models import (
     Sprint,
     SprintBoardPreference,
     Task,
     TaskHistory,
+    TaskWorkSession,
 )
 
 
@@ -309,4 +315,81 @@ def change_sprint_status(*, sprint_id, status):
             }
         ) from error
 
-    return sprint, True
\ No newline at end of file
+    return sprint, True
+
+
+def work_time_unavailable_reason(task, user):
+    """Shared by the UI and service; hiding a button alone is not authorization."""
+    if task.is_deleted or not task.sprint_id:
+        return "Time can only be recorded for a Sprint task."
+    if task.sprint.status != "active":
+        return "Time can only be recorded in an active Sprint."
+    if task.status == "completed":
+        return "Completed tasks cannot receive new or edited time entries."
+    if task.assignee_id != user.pk or not task.sprint.team_members.filter(pk=user.pk).exists():
+        return "Only a Sprint member assigned to this task can record or edit time."
+    return ""
+
+
+def _work_session_total(task):
+    interval = ExpressionWrapper(F("ended_at") - F("started_at"), output_field=DurationField())
+    return task.work_sessions.aggregate(total=Sum(interval))["total"] or timedelta()
+
+
+def _duration_hours(duration):
+    return (Decimal(str(duration.total_seconds())) / Decimal("3600")).quantize(
+        Decimal("0.01"), rounding=ROUND_HALF_UP,
+    )
+
+
+@transaction.atomic
+def save_work_session(*, task_id, user, started_at, ended_at, session_id=None):
+    """Validate and save a work interval together with the task's accumulated total."""
+    # Serialize this user's writes across ALL tasks, including when no entry exists yet.
+    get_user_model().objects.select_for_update().get(pk=user.pk)
+    task = Task.objects.select_for_update().get(pk=task_id, is_deleted=False)
+    if task.sprint_id:
+        # Re-read/lock the Sprint so a concurrent status change cannot bypass validation.
+        task.sprint = Sprint.objects.select_for_update().get(pk=task.sprint_id)
+    reason = work_time_unavailable_reason(task, user)
+    if reason:
+        if task.sprint_id and task.assignee_id != user.pk:
+            raise PermissionDenied(reason)
+        if task.sprint_id and not task.sprint.team_members.filter(pk=user.pk).exists():
+            raise PermissionDenied(reason)
+        raise ValidationError(reason)
+    if ended_at <= started_at:
+        raise ValidationError("End date and time must be after start date and time.")
+
+    entry = TaskWorkSession(task=task, user=user)
+    previous_duration = timedelta()
+    if session_id is not None:
+        # Scope edits to both the requested task and the authenticated owner.
+        entry = TaskWorkSession.objects.select_for_update().get(
+            pk=session_id, task=task, user=user,
+        )
+        previous_duration = entry.duration
+
+    overlaps = TaskWorkSession.objects.filter(
+        user=user, started_at__lt=ended_at, ended_at__gt=started_at,
+    )
+    if entry.pk:
+        overlaps = overlaps.exclude(pk=entry.pk)
+    if overlaps.exists():
+        raise ValidationError("This interval overlaps another of your work sessions (including on other tasks).")
+
+    previous_total = _work_session_total(task)
+    # Preserve legacy aggregate hours, whose individual timestamps are unavailable.
+    legacy_hours = task.accumulated_hours - _duration_hours(previous_total)
+    new_duration = ended_at - started_at
+    total_hours = legacy_hours + _duration_hours(previous_total - previous_duration + new_duration)
+    if total_hours > Decimal("9999.99"):
+        raise ValidationError("Total task time cannot exceed 9999.99 hours.")
+
+    entry.started_at = started_at
+    entry.ended_at = ended_at
+    entry.save()
+    task.accumulated_hours = total_hours
+    task.save(update_fields=["accumulated_hours", "updated_at"])
+    # Time history lives in work_sessions, not the shared TaskHistory panel (AC 13).
+    return entry
```

### backlog/sprint_views.py

新增记录和修改的 POST 处理函数；记录人来自 request.user，修改记录必须同时属于当前用户和指定任务；错误保留输入，成功后重定向；看板 API 增加 accumulated_hours。

```diff
diff --git a/backlog/sprint_views.py b/backlog/sprint_views.py
index 84254f2..6957a1d 100644
--- a/backlog/sprint_views.py
+++ b/backlog/sprint_views.py
@@ -1,13 +1,15 @@
 from django.contrib.auth.decorators import login_required
 from django.core.exceptions import ValidationError
 from django.http import JsonResponse
-from django.shortcuts import get_object_or_404
+from django.shortcuts import get_object_or_404, redirect
+from django.contrib import messages
 from django.views.decorators.http import require_GET, require_POST
 
 from .models import (
     Sprint,
     SprintBoardPreference,
     Task,
+    TaskWorkSession,
 )
 
 from .sprint_forms import (
@@ -15,6 +17,7 @@ from .sprint_forms import (
     SprintBoardViewForm,
     SprintStatusForm,
     SprintTaskStatusForm,
+    WorkSessionForm,
 )
 
 from .sprint_services import (
@@ -22,6 +25,7 @@ from .sprint_services import (
     change_sprint_task_status,
     move_task,
     save_board_preference,
+    save_work_session,
 )
 
 
@@ -35,6 +39,51 @@ def _form_errors(form):
     }
 
 
+@login_required
+@require_POST
+def record_task_time(request, task_id):
+    return _save_task_time(request, task_id)
+
+
+@login_required
+@require_POST
+def edit_task_time(request, task_id, session_id):
+    return _save_task_time(request, task_id, session_id)
+
+
+def _save_task_time(request, task_id, session_id=None):
+    from .views import render_task_detail
+
+    task = get_object_or_404(Task.objects.select_related("sprint"), pk=task_id, is_deleted=False)
+    editing_session = None
+    if session_id is not None:
+        editing_session = get_object_or_404(TaskWorkSession, pk=session_id, task=task, user=request.user)
+    is_edit = session_id is not None
+    form = WorkSessionForm(request.POST, auto_id="edit_%s" if is_edit else "record_%s")
+    status = 400
+    if form.is_valid():
+        try:
+            save_work_session(
+                task_id=task.pk, user=request.user, session_id=session_id,
+                started_at=form.cleaned_data["started_at"], ended_at=form.cleaned_data["ended_at"],
+            )
+        except (Task.DoesNotExist, TaskWorkSession.DoesNotExist):
+            # A task/entry may disappear between initial lookup and the transaction.
+            from django.http import Http404
+            raise Http404("The task or work session no longer exists.")
+        except ValidationError as error:
+            form.add_error(None, error)
+        else:
+            messages.success(request, "Work session updated." if is_edit else "Work session recorded.")
+            return redirect("backlog:task_detail", task_id=task.pk)
+    task.refresh_from_db()
+    return render_task_detail(
+        request, task, editing_session=editing_session,
+        open_time_modal="editTimeModal" if is_edit else "recordTimeModal", status=status,
+        **({"edit_time_form": form} if is_edit else {"time_form": form}),
+    )
+
+
 def _validation_errors(error):
     if hasattr(error, 'message_dict'):
         return error.message_dict
@@ -55,6 +104,7 @@ def _task_payload(task):
         'status': task.status,
         'status_label': task.get_status_display(),
         'sprint_id': task.sprint_id,
+        'accumulated_hours': str(task.accumulated_hours),
         'assignee': (
             task.assignee.get_full_name()
             or task.assignee.username
@@ -370,4 +420,4 @@ def sprint_status_endpoint(request, sprint_id):
                 ),
             },
         }
-    )
\ No newline at end of file
+    )
```

### backlog/urls.py

新增 tasks/<task_id>/time/ 和 tasks/<task_id>/time/<session_id>/edit/ 两条路由。

```diff
diff --git a/backlog/urls.py b/backlog/urls.py
index f995389..a79f26d 100644
--- a/backlog/urls.py
+++ b/backlog/urls.py
@@ -27,6 +27,10 @@ urlpatterns = [
     # US-16
     path("tasks/<int:task_id>/sprint-status/", sprint_views.sprint_task_status_endpoint, name="sprint_task_status"),
 
+    # US-19: Owner-scoped work session creation and editing.
+    path("tasks/<int:task_id>/time/", sprint_views.record_task_time, name="record_task_time"),
+    path("tasks/<int:task_id>/time/<int:session_id>/edit/", sprint_views.edit_task_time, name="edit_task_time"),
+
     # US-17
     path("sprints/<int:sprint_id>/board/data/", sprint_views.sprint_board_data, name="sprint_board_data"),
     path("sprints/<int:sprint_id>/board/view/", sprint_views.sprint_board_view_endpoint, name="sprint_board_view"),
```

### backlog/views.py

任务详情加入当前用户的工时记录、表单及不可操作原因；任务编辑只保存表单中的数据库字段，避免用旧实例覆盖另一请求新增的累计工时。

```diff
diff --git a/backlog/views.py b/backlog/views.py
index bf91564..8538f9a 100644
--- a/backlog/views.py
+++ b/backlog/views.py
@@ -4,6 +4,9 @@ from django.contrib.auth.decorators import login_required
 from .forms import SprintCreateForm, SprintEditForm, TaskCreateForm, TaskEditForm
 from django.db.models import Sum, Q, Case, When, Value, IntegerField
 from .models import Task, Tag, Sprint, SprintHistory, TaskHistory, SprintBoardPreference
+from .sprint_forms import WorkSessionForm
+from .sprint_services import work_time_unavailable_reason
+from django.utils import timezone
 
 
 @login_required
@@ -165,16 +168,23 @@ def task_detail(request, task_id):
         is_deleted=False
     )
 
-    history = task.history.all()
+    return render_task_detail(request, task)
 
-    return render(
-        request,
-        "backlog/task_detail.html",
-        {
-            "task": task,
-            "history": history,
-        },
-    )
+
+def render_task_detail(request, task, *, time_form=None, edit_time_form=None,
+                       editing_session=None, open_time_modal="", status=200):
+    """Use the same detail page for initial display and recoverable form errors."""
+    return render(request, "backlog/task_detail.html", {
+        "task": task,
+        "history": task.history.all(),
+        "time_entries": task.work_sessions.filter(user=request.user),
+        "time_unavailable_reason": work_time_unavailable_reason(task, request.user),
+        "time_form": time_form if time_form is not None else WorkSessionForm(auto_id="record_%s"),
+        "edit_time_form": edit_time_form if edit_time_form is not None else WorkSessionForm(auto_id="edit_%s"),
+        "editing_session": editing_session,
+        "open_time_modal": open_time_modal,
+        "time_zone": timezone.get_current_timezone_name(),
+    }, status=status)
 
 
 @login_required
@@ -236,7 +246,10 @@ def edit_task(request, task_id):
 
         if form.is_valid():
             changed_fields = form.changed_data
-            task = form.save()
+            task = form.save(commit=False)
+            # A concurrent time submission must not be overwritten by this older form instance.
+            task.save(update_fields=[field for field in form._meta.fields if field != "tags"] + ["updated_at"])
+            form.save_m2m()
 
             if changed_fields:
                 for field in changed_fields:
```

### backlog/forms.py

从 TaskCreateForm 和 TaskEditForm 移除 accumulated_hours 字段及手填校验；总工时改由记录服务管理，恶意 POST 的同名字段也不会被保存。

```diff
diff --git a/backlog/forms.py b/backlog/forms.py
index fa015be..df85863 100644
--- a/backlog/forms.py
+++ b/backlog/forms.py
@@ -191,7 +191,6 @@ class TaskCreateForm(forms.ModelForm):
             "title",
             "item_type",
             "story_points",
-            "accumulated_hours",
             "tags",
             "priority",
             "assignee",
@@ -216,14 +215,6 @@ class TaskCreateForm(forms.ModelForm):
                     "step": 1,
                 }
             ),
-            "accumulated_hours": forms.NumberInput(
-                attrs={
-                    "class": "form-control",
-                    "min": 0,
-                    "step": "0.1",
-                    "placeholder": "0.0",
-                }
-            ),
             "tags": forms.CheckboxSelectMultiple,
             "priority": forms.Select(
                 attrs={"class": "form-select"}
@@ -249,11 +240,9 @@ class TaskCreateForm(forms.ModelForm):
         self.fields["description"].required = True
         self.fields["tags"].required = True
         self.fields["assignee"].required = True
-        self.fields["accumulated_hours"].required = False
 
         self.fields["item_type"].initial = "story"
         self.fields["story_points"].initial = 0
-        self.fields["accumulated_hours"].initial = 0.0
         self.fields["priority"].initial = "medium"
         self.fields["status"].initial = "not_started"
         self.fields["stage"].initial = "planning"
@@ -282,12 +271,6 @@ class TaskCreateForm(forms.ModelForm):
 
         return story_points
 
-    def clean_accumulated_hours(self):
-        hours = self.cleaned_data.get("accumulated_hours")
-        if hours is not None and hours < 0:
-            raise forms.ValidationError("Accumulated hours cannot be negative.")
-        return hours if hours is not None else 0.0
-
     def clean_attachment(self):
         attachment = self.cleaned_data.get("attachment")
 
@@ -308,7 +291,6 @@ class TaskEditForm(forms.ModelForm):
             "title",
             "item_type",
             "story_points",
-            "accumulated_hours",
             "tags",
             "priority",
             "assignee",
@@ -333,14 +315,6 @@ class TaskEditForm(forms.ModelForm):
                     "step": 1,
                 }
             ),
-            "accumulated_hours": forms.NumberInput(
-                attrs={
-                    "class": "form-control",
-                    "min": 0,
-                    "step": "0.1",
-                    "placeholder": "0.0",
-                }
-            ),
             "tags": forms.CheckboxSelectMultiple,
             "priority": forms.Select(
                 attrs={"class": "form-select"}
@@ -366,7 +340,6 @@ class TaskEditForm(forms.ModelForm):
         self.fields["description"].required = True
         self.fields["tags"].required = True
         self.fields["assignee"].required = True
-        self.fields["accumulated_hours"].required = False
 
         User = get_user_model()
         user_queryset = User.objects.filter(is_superuser=False).order_by("first_name", "last_name", "username")
@@ -389,9 +362,3 @@ class TaskEditForm(forms.ModelForm):
             )
 
         return story_points
-
-    def clean_accumulated_hours(self):
-        hours = self.cleaned_data.get("accumulated_hours")
-        if hours is not None and hours < 0:
-            raise forms.ValidationError("Accumulated hours cannot be negative.")
-        return hours if hours is not None else 0.0    
\ No newline at end of file
```

### backlog/admin.py

将 TaskAdmin 的 accumulated_hours 设为只读，避免手工改坏汇总结果。

```diff
diff --git a/backlog/admin.py b/backlog/admin.py
index 0abc3e1..a6e52c2 100644
--- a/backlog/admin.py
+++ b/backlog/admin.py
@@ -51,6 +51,7 @@ class SprintHistoryAdmin(admin.ModelAdmin):
 
 @admin.register(Task)
 class TaskAdmin(admin.ModelAdmin):
+    readonly_fields = ('accumulated_hours',)
     list_display = (
         'title',
         'item_type',
```

### backlog/templatetags/__init__.py

新增空文件，让 Django 识别自定义模板标签包。

```diff
diff --git a/backlog/templatetags/__init__.py b/backlog/templatetags/__init__.py
new file mode 100644
index 0000000..e69de29
--- /dev/null
+++ b/backlog/templatetags/__init__.py
```

### backlog/templatetags/work_time.py

新增 hours_duration 模板过滤器，将十进制小时显示为 3h 15m。

```diff
diff --git a/backlog/templatetags/work_time.py b/backlog/templatetags/work_time.py
new file mode 100644
--- /dev/null
+++ b/backlog/templatetags/work_time.py
@@ -0,0 +1,13 @@
+from decimal import Decimal, ROUND_HALF_UP
+
+from django import template
+
+register = template.Library()
+
+
+@register.filter
+def hours_duration(value):
+    """Display the existing decimal-hours total as hours and minutes."""
+    total_minutes = int((Decimal(str(value or 0)) * 60).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
+    hours, minutes = divmod(total_minutes, 60)
+    return f"{hours}h {minutes:02d}m"
```

### templates/backlog/task_detail.html

沿用详情页和两个弹窗的样式，把写死的 Logged 2 hours、14h 00m 换成真实数据；仅展示当前用户自己的记录；合资格时才显示操作按钮；Sprint 任务返回看板。

```diff
diff --git a/templates/backlog/task_detail.html b/templates/backlog/task_detail.html
index e74ea09..c6b7d03 100644
--- a/templates/backlog/task_detail.html
+++ b/templates/backlog/task_detail.html
@@ -1,5 +1,5 @@
 {% extends 'base.html' %}
-{% load static %}
+{% load static work_time tz %}
 
 {% block title %}{{ task.title }} | AgileFlow{% endblock %}
 
@@ -7,8 +7,8 @@
 <div class="container-fluid px-4 py-3">
 
     <!-- Back link -->
-    <a href="{% url 'backlog:product_backlog' %}" class="back-link d-inline-flex align-items-center gap-1 mb-3">
-        <i class="bi bi-arrow-left"></i> Back to Backlog
+    <a href="{% if task.sprint_id %}{% url 'backlog:sprint_board_detail' task.sprint_id %}{% else %}{% url 'backlog:product_backlog' %}{% endif %}" class="back-link d-inline-flex align-items-center gap-1 mb-3">
+        <i class="bi bi-arrow-left"></i> {% if task.sprint_id %}Back to Sprint Board{% else %}Back to Backlog{% endif %}
     </a>
 
     <!-- Task Title -->
@@ -42,18 +42,19 @@
             </div>
         </div>
 
-        <!-- RIGHT: Time Tracking & History -->
+        <!-- RIGHT: Task activity panels -->
         <div class="col-lg-6 d-flex flex-column gap-4">
             
-            {% if task.sprint and task.sprint.status == 'active' %}
-            <!-- Time Tracking (GUI ONLY) -->
+            {% if task.sprint_id %}
+            <!-- US-19: Real work sessions, scoped to the current user. -->
             <div class="detail-panel p-4 bg-white border rounded-3 shadow-sm transition-all">
                 <div class="d-flex align-items-center justify-content-between border-bottom pb-2 mb-3">
                     <div class="fs-5 fw-bold text-dark"><i class="bi bi-clock-history me-2 text-primary"></i>Time Tracking</div>
                 </div>
                 
                 <div class="time-log-list d-flex flex-column gap-2">
-                    <!-- Current User's Time Log -->
+                    <div class="text-muted small">Your work sessions ({{ time_zone }})</div>
+                    {% for session in time_entries %}
                     <div class="d-flex justify-content-between align-items-center p-3 bg-primary-subtle rounded border border-primary-subtle">
                         <div class="d-flex align-items-center gap-2">
                             <div class="user-avatar rounded-circle d-flex align-items-center justify-content-center text-white" style="width: 32px; height: 32px; font-size: 0.85rem;">
@@ -61,25 +62,38 @@
                             </div>
                             <div>
                                 <div class="fw-semibold text-dark" style="font-size: 0.9rem;">{{ user.first_name|default:user.username }}</div>
-                                <div class="text-muted" style="font-size: 0.8rem;">Logged 2 hours</div>
+                                <div class="text-muted" style="font-size: 0.8rem;">{{ session.started_at|localtime|date:"d M Y H:i" }} – {{ session.ended_at|localtime|date:"d M Y H:i" }}</div>
+                                <div class="text-primary small">Logged {{ session.duration_label }}</div>
                             </div>
                         </div>
-                        <button type="button" class="btn btn-sm btn-light border shadow-sm text-primary d-flex align-items-center gap-1 px-2" data-bs-toggle="modal" data-bs-target="#editTimeModal">
+                        {% if not time_unavailable_reason %}
+                        <button type="button" class="btn btn-sm btn-light border shadow-sm text-primary d-flex align-items-center gap-1 px-2" data-bs-toggle="modal" data-bs-target="#editTimeModal"
+                                data-edit-url="{% url 'backlog:edit_task_time' task.id session.id %}"
+                                data-start-date="{{ session.started_at|localtime|date:'Y-m-d' }}" data-start-time="{{ session.started_at|localtime|date:'H:i' }}"
+                                data-end-date="{{ session.ended_at|localtime|date:'Y-m-d' }}" data-end-time="{{ session.ended_at|localtime|date:'H:i' }}">
                             <i class="bi bi-pencil-square"></i> <span style="font-size: 0.85rem;">Edit</span>
                         </button>
+                        {% endif %}
                     </div>
+                    {% empty %}
+                    <p class="text-muted small mb-0">You have not logged any work sessions for this task.</p>
+                    {% endfor %}
                 </div>
                 
                 <!-- Total -->
                 <div class="d-flex justify-content-between align-items-center mt-3 pt-3 border-top">
                     <span class="fs-6 fw-semibold text-secondary">Total Time Spent</span>
-                    <span class="fs-5 fw-bold text-primary">14h 00m</span>
+                    <span class="fs-5 fw-bold text-primary">{{ task.accumulated_hours|hours_duration }}</span>
                 </div>
                 
                 <div class="mt-4">
+                    {% if not time_unavailable_reason %}
                     <button type="button" class="btn btn-primary w-100 d-flex align-items-center justify-content-center gap-2 py-2 fw-medium shadow-sm" data-bs-toggle="modal" data-bs-target="#recordTimeModal">
                         <i class="bi bi-plus-circle"></i> Record Time Spent
                     </button>
+                    {% else %}
+                    <p class="text-muted small mb-0">{{ time_unavailable_reason }}</p>
+                    {% endif %}
                 </div>
             </div>
             {% endif %}
@@ -128,8 +142,8 @@
 
 </div>
 
-<!-- Record Time Spent Modal -->
-<div class="modal fade" id="recordTimeModal" tabindex="-1" aria-labelledby="recordTimeModalLabel" aria-hidden="true">
+{% if not time_unavailable_reason %}
+<div class="modal fade" id="recordTimeModal" tabindex="-1" aria-labelledby="recordTimeModalLabel" aria-hidden="true" data-open-time-modal="{{ open_time_modal }}">
   <div class="modal-dialog modal-dialog-centered">
     <div class="modal-content border-0 shadow rounded-4">
       <div class="modal-header border-bottom-0 pb-0 pt-4 px-4">
@@ -138,46 +152,14 @@
       </div>
       <div class="modal-body px-4 pb-4 pt-3">
         <p class="text-muted mb-4">Log the hours you spent working on <strong>{{ task.title }}</strong>.</p>
-        <form>
-            <div class="row g-2 mb-3">
-                <div class="col-sm-6">
-                    <div class="form-floating">
-                        <input type="date" class="form-control default-today" id="recordStartDate" name="start_date" required>
-                        <label for="recordStartDate" class="text-muted">Start Date</label>
-                    </div>
-                </div>
-                <div class="col-sm-6">
-                    <div class="form-floating">
-                        <input type="time" class="form-control default-now" id="recordStartTime" name="start_time" required>
-                        <label for="recordStartTime" class="text-muted">Start Time</label>
-                    </div>
-                </div>
-            </div>
-            <div class="row g-2 mb-4">
-                <div class="col-sm-6">
-                    <div class="form-floating">
-                        <input type="date" class="form-control default-today" id="recordEndDate" name="end_date" required>
-                        <label for="recordEndDate" class="text-muted">End Date</label>
-                    </div>
-                </div>
-                <div class="col-sm-6">
-                    <div class="form-floating">
-                        <input type="time" class="form-control default-now" id="recordEndTime" name="end_time" required>
-                        <label for="recordEndTime" class="text-muted">End Time</label>
-                    </div>
-                </div>
-            </div>
-            <div class="d-flex justify-content-end gap-2">
-                <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancel</button>
-                <button type="button" class="btn btn-primary px-4 shadow-sm" data-bs-dismiss="modal">Record Time</button>
-            </div>
+        <form method="post" action="{% url 'backlog:record_task_time' task.id %}" class="work-session-form">
+          {% csrf_token %}
+          {% include "backlog/_work_session_form.html" with form=time_form submit_label="Record Time" %}
         </form>
       </div>
     </div>
   </div>
 </div>
-
-<!-- Edit Time Spent Modal -->
 <div class="modal fade" id="editTimeModal" tabindex="-1" aria-labelledby="editTimeModalLabel" aria-hidden="true">
   <div class="modal-dialog modal-dialog-centered">
     <div class="modal-content border-0 shadow rounded-4">
@@ -187,63 +169,19 @@
       </div>
       <div class="modal-body px-4 pb-4 pt-3">
         <p class="text-muted mb-4">Update your logged hours for this task.</p>
-        <form>
-            <div class="row g-2 mb-3">
-                <div class="col-sm-6">
-                    <div class="form-floating">
-                        <input type="date" class="form-control default-today" id="editStartDate" name="start_date" required>
-                        <label for="editStartDate" class="text-muted">Start Date</label>
-                    </div>
-                </div>
-                <div class="col-sm-6">
-                    <div class="form-floating">
-                        <input type="time" class="form-control default-now" id="editStartTime" name="start_time" required>
-                        <label for="editStartTime" class="text-muted">Start Time</label>
-                    </div>
-                </div>
-            </div>
-            <div class="row g-2 mb-4">
-                <div class="col-sm-6">
-                    <div class="form-floating">
-                        <input type="date" class="form-control default-today" id="editEndDate" name="end_date" required>
-                        <label for="editEndDate" class="text-muted">End Date</label>
-                    </div>
-                </div>
-                <div class="col-sm-6">
-                    <div class="form-floating">
-                        <input type="time" class="form-control default-now" id="editEndTime" name="end_time" required>
-                        <label for="editEndTime" class="text-muted">End Time</label>
-                    </div>
-                </div>
-            </div>
-            <div class="d-flex justify-content-end gap-2">
-                <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancel</button>
-                <button type="button" class="btn btn-primary px-4 shadow-sm" data-bs-dismiss="modal">Save Changes</button>
-            </div>
+        <form method="post" action="{% if editing_session %}{% url 'backlog:edit_task_time' task.id editing_session.id %}{% endif %}" class="work-session-form">
+          {% csrf_token %}
+          {% include "backlog/_work_session_form.html" with form=edit_time_form submit_label="Save Changes" %}
         </form>
       </div>
     </div>
   </div>
 </div>
+{% elif time_form.errors or edit_time_form.errors %}
+<div class="alert alert-danger" role="alert">{{ time_form.errors }}{{ edit_time_form.errors }}</div>
+{% endif %}
+{% endblock %}
 
-<script>
-    document.addEventListener('DOMContentLoaded', function() {
-        const now = new Date();
-        const year = now.getFullYear();
-        const month = String(now.getMonth() + 1).padStart(2, '0');
-        const day = String(now.getDate()).padStart(2, '0');
-        const dateStr = `${year}-${month}-${day}`;
-        
-        const hours = String(now.getHours()).padStart(2, '0');
-        const minutes = String(now.getMinutes()).padStart(2, '0');
-        const timeStr = `${hours}:${minutes}`;
-
-        document.querySelectorAll('input[type="date"].default-today').forEach(el => {
-            if (!el.value) el.value = dateStr;
-        });
-        document.querySelectorAll('input[type="time"].default-now').forEach(el => {
-            if (!el.value) el.value = timeStr;
-        });
-    });
-</script>
+{% block extra_js %}
+<script src="{% static 'js/task_time.js' %}"></script>
 {% endblock %}
```

### templates/backlog/_work_session_form.html

新增共用表单模板，Record/Edit 共用相同字段、日历与时钟输入、CSRF 保护、错误提示和提交按钮。

```diff
diff --git a/templates/backlog/_work_session_form.html b/templates/backlog/_work_session_form.html
new file mode 100644
--- /dev/null
+++ b/templates/backlog/_work_session_form.html
@@ -0,0 +1,31 @@
+{% if form.errors %}
+<div class="alert alert-danger" role="alert">
+    {{ form.non_field_errors }}
+    {% for field in form %}{% for error in field.errors %}<div>{{ field.label }}: {{ error }}</div>{% endfor %}{% endfor %}
+</div>
+{% endif %}
+<p class="text-muted small">Times are in {{ time_zone }}. Duration is calculated automatically.</p>
+<div class="row g-2 mb-3">
+    <div class="col-sm-6"><div class="form-floating">
+        {{ form.start_date }}
+        <label for="{{ form.start_date.id_for_label }}"><i class="bi bi-calendar3 me-1"></i>Start Date</label>
+    </div></div>
+    <div class="col-sm-6"><div class="form-floating">
+        {{ form.start_time }}
+        <label for="{{ form.start_time.id_for_label }}"><i class="bi bi-clock me-1"></i>Start Time</label>
+    </div></div>
+</div>
+<div class="row g-2 mb-4">
+    <div class="col-sm-6"><div class="form-floating">
+        {{ form.end_date }}
+        <label for="{{ form.end_date.id_for_label }}"><i class="bi bi-calendar3 me-1"></i>End Date</label>
+    </div></div>
+    <div class="col-sm-6"><div class="form-floating">
+        {{ form.end_time }}
+        <label for="{{ form.end_time.id_for_label }}"><i class="bi bi-clock me-1"></i>End Time</label>
+    </div></div>
+</div>
+<div class="d-flex justify-content-end gap-2">
+    <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancel</button>
+    <button type="submit" class="btn btn-primary px-4 shadow-sm">{{ submit_label }}</button>
+</div>
```

### templates/backlog/sprint_board.html

在 Not started、Active、Completed 三列的任务卡片中显示真实总工时；徽章放在已有优先级徽章之后，保持原拖拽脚本的选择器工作。

```diff
diff --git a/templates/backlog/sprint_board.html b/templates/backlog/sprint_board.html
index 910d3ad..21f258c 100644
--- a/templates/backlog/sprint_board.html
+++ b/templates/backlog/sprint_board.html
@@ -1,5 +1,5 @@
 {% extends "base.html" %}
-{% load static %}
+{% load static work_time %}
 
 {% block title %}{{ current_sprint.name|default:"Sprint Board" }} | AgileFlow{% endblock %}
 
@@ -121,6 +121,7 @@
                         {% if task.assignee %}
                         <span class="fw-semibold"><i class="bi bi-person"></i> {{ task.assignee.get_full_name|default:task.assignee.username }}</span>
                         {% endif %}
+                        <span class="badge bg-primary-subtle text-primary rounded-pill px-2"><i class="bi bi-clock"></i> Total time: {{ task.accumulated_hours|hours_duration }}</span>
                     </div>
                 </a>
                 {% empty %}
@@ -157,6 +158,7 @@
                         {% if task.assignee %}
                         <span class="fw-semibold"><i class="bi bi-person"></i> {{ task.assignee.get_full_name|default:task.assignee.username }}</span>
                         {% endif %}
+                        <span class="badge bg-primary-subtle text-primary rounded-pill px-2"><i class="bi bi-clock"></i> Total time: {{ task.accumulated_hours|hours_duration }}</span>
                     </div>
                 </a>
                 {% empty %}
@@ -193,6 +195,7 @@
                         {% if task.assignee %}
                         <span class="fw-semibold"><i class="bi bi-person"></i> {{ task.assignee.get_full_name|default:task.assignee.username }}</span>
                         {% endif %}
+                        <span class="badge bg-primary-subtle text-primary rounded-pill px-2"><i class="bi bi-clock"></i> Total time: {{ task.accumulated_hours|hours_duration }}</span>
                     </div>
                 </a>
                 {% empty %}
@@ -411,4 +414,4 @@
     });
 </script>
 <script src="{% static 'js/sprint_board.js' %}"></script>
-{% endblock %}
\ No newline at end of file
+{% endblock %}
```

### static/js/task_time.js

新增编辑弹窗数据填充：点击某条记录的 Edit 时，加载该记录的四个时间值和专属提交地址；校验失败时自动重新打开对应弹窗；阻止重复点击提交。

```diff
diff --git a/static/js/task_time.js b/static/js/task_time.js
new file mode 100644
--- /dev/null
+++ b/static/js/task_time.js
@@ -0,0 +1,34 @@
+/** US-19: Populate the existing edit modal with the selected real work session. */
+document.addEventListener('DOMContentLoaded', () => {
+    const editModal = document.getElementById('editTimeModal');
+    editModal?.addEventListener('show.bs.modal', (event) => {
+        const button = event.relatedTarget;
+        if (!button) return; // Server validation errors retain the submitted values.
+        const form = editModal.querySelector('form');
+        form.action = button.dataset.editUrl;
+        for (const [field, attribute] of [
+            ['start_date', 'startDate'], ['start_time', 'startTime'],
+            ['end_date', 'endDate'], ['end_time', 'endTime'],
+        ]) {
+            form.elements[field].value = button.dataset[attribute];
+        }
+        editModal.querySelectorAll('.alert-danger').forEach((alert) => alert.remove());
+    });
+
+    const reopen = document.querySelector('[data-open-time-modal]')?.dataset.openTimeModal;
+    if (reopen && window.bootstrap) {
+        const modal = document.getElementById(reopen);
+        if (modal) bootstrap.Modal.getOrCreateInstance(modal).show();
+    }
+
+    document.querySelectorAll('.work-session-form').forEach((form) => {
+        form.addEventListener('submit', (event) => {
+            if (form.dataset.submitting) {
+                event.preventDefault();
+                return;
+            }
+            form.dataset.submitting = 'true';
+            form.querySelector('[type="submit"]').disabled = true;
+        });
+    });
+});
```

### backlog/tests/test_us19_record_time.py

新增 33 项测试，覆盖验收标准与权限、格式、边界、跨任务重叠、跨天、舍入、编辑归属、回滚、CSRF 和汇总保护。

```diff
diff --git a/backlog/tests/test_us19_record_time.py b/backlog/tests/test_us19_record_time.py
new file mode 100644
--- /dev/null
+++ b/backlog/tests/test_us19_record_time.py
@@ -0,0 +1,308 @@
+from datetime import timedelta
+from decimal import Decimal
+
+from django.contrib.auth.models import User
+from django.db import IntegrityError, transaction
+from django.test import Client, TestCase
+from django.urls import reverse
+from django.utils import timezone
+
+from backlog.forms import TaskCreateForm, TaskEditForm
+from backlog.models import Sprint, Tag, Task, TaskHistory, TaskWorkSession
+from backlog.sprint_forms import WorkSessionForm
+
+
+class US19RecordTimeTests(TestCase):
+    """Acceptance coverage through the actual POST endpoints and rendered pages."""
+
+    def setUp(self):
+        self.user = User.objects.create_user(username="time_member")
+        self.other = User.objects.create_user(username="other_member")
+        self.sprint = Sprint.objects.create(name="Time tracking Sprint", status="active")
+        self.sprint.team_members.add(self.user, self.other)
+        self.task = Task.objects.create(title="US19 task", sprint=self.sprint, assignee=self.user)
+        self.client.force_login(self.user)
+        self.url = reverse("backlog:record_task_time", args=[self.task.pk])
+
+    def payload(self, start="09:00", end="10:00", **overrides):
+        data = {"start_date": "2026-09-30", "start_time": start,
+                "end_date": "2026-09-30", "end_time": end}
+        return {**data, **overrides}
+
+    def record(self, start="09:00", end="10:00", **overrides):
+        return self.client.post(self.url, self.payload(start, end, **overrides))
+
+    def edit_url(self, session):
+        return reverse("backlog:edit_task_time", args=[self.task.pk, session.pk])
+
+    def test_record_calculates_duration_and_member_automatically(self):
+        response = self.record("09:00", "10:30", user_id=self.other.pk, duration="999")
+        self.assertRedirects(response, reverse("backlog:task_detail", args=[self.task.pk]))
+        session = TaskWorkSession.objects.get()
+        self.assertEqual(session.user, self.user)
+        self.assertEqual(session.task, self.task)
+        self.assertEqual(session.duration, timedelta(minutes=90))
+        self.assertEqual(timezone.localtime(session.started_at).strftime("%H:%M"), "09:00")
+        self.assertTrue(timezone.is_aware(session.started_at))
+        self.task.refresh_from_db()
+        self.assertEqual(self.task.accumulated_hours, Decimal("1.50"))
+
+    def test_multiple_sessions_accumulate_without_rounding_each_session(self):
+        for hour in range(9, 14):
+            self.assertEqual(self.record(f"{hour:02}:00", f"{hour:02}:01").status_code, 302)
+        self.task.refresh_from_db()
+        self.assertEqual(TaskWorkSession.objects.count(), 5)
+        self.assertEqual(self.task.accumulated_hours, Decimal("0.08"))
+
+    def test_overnight_and_multiple_day_sessions(self):
+        self.assertEqual(self.record("23:30", "01:00", end_date="2026-10-02").status_code, 302)
+        self.assertEqual(TaskWorkSession.objects.get().duration, timedelta(hours=25, minutes=30))
+
+    def test_legacy_aggregate_hours_are_preserved(self):
+        self.task.accumulated_hours = Decimal("4.50")
+        self.task.save()
+        self.record()
+        self.task.refresh_from_db()
+        self.assertEqual(self.task.accumulated_hours, Decimal("5.50"))
+
+    def test_only_assigned_sprint_member_can_record(self):
+        self.client.force_login(self.other)
+        self.assertEqual(self.record().status_code, 403)
+        self.assertFalse(TaskWorkSession.objects.exists())
+
+    def test_assignee_must_also_be_a_sprint_member(self):
+        self.sprint.team_members.remove(self.user)
+        self.assertEqual(self.record().status_code, 403)
+        self.assertFalse(TaskWorkSession.objects.exists())
+
+    def test_admin_does_not_bypass_assignment(self):
+        self.other.is_staff = self.other.is_superuser = True
+        self.other.save()
+        self.client.force_login(self.other)
+        self.assertEqual(self.record().status_code, 403)
+
+    def test_login_required_for_create_and_edit(self):
+        self.record()
+        session = TaskWorkSession.objects.get()
+        self.client.logout()
+        self.assertEqual(self.record().status_code, 302)
+        self.assertEqual(self.client.post(self.edit_url(session), self.payload()).status_code, 302)
+        self.assertEqual(TaskWorkSession.objects.count(), 1)
+
+    def test_endpoints_require_post(self):
+        self.record()
+        self.assertEqual(self.client.get(self.url).status_code, 405)
+        self.assertEqual(self.client.get(self.edit_url(TaskWorkSession.objects.get())).status_code, 405)
+
+    def test_csrf_is_enforced(self):
+        client = Client(enforce_csrf_checks=True)
+        client.force_login(self.user)
+        self.assertEqual(client.post(self.url, self.payload()).status_code, 403)
+        self.assertFalse(TaskWorkSession.objects.exists())
+
+    def test_required_fields_and_malformed_dates_are_rejected(self):
+        for field in self.payload():
+            with self.subTest(field=field):
+                data = self.payload()
+                data.pop(field)
+                self.assertEqual(self.client.post(self.url, data).status_code, 400)
+        for overrides in ({"start_date": "2026-02-30"}, {"end_date": "invalid"},
+                          {"start_time": "25:00"}, {"end_time": "invalid"}):
+            with self.subTest(overrides=overrides):
+                self.assertEqual(self.record(**overrides).status_code, 400)
+        self.assertFalse(TaskWorkSession.objects.exists())
+
+    def test_equal_or_reversed_timestamps_are_rejected(self):
+        self.assertEqual(self.record("10:00", "10:00").status_code, 400)
+        self.assertEqual(self.record("11:00", "10:00").status_code, 400)
+        self.assertEqual(self.record(end_date="2026-09-29").status_code, 400)
+        self.assertFalse(TaskWorkSession.objects.exists())
+
+    def test_errors_preserve_values_and_reopen_record_modal(self):
+        response = self.record("11:00", "10:00")
+        self.assertContains(response, "End date and time must be after", status_code=400)
+        self.assertContains(response, 'value="11:00"', status_code=400)
+        self.assertContains(response, 'data-open-time-modal="recordTimeModal"', status_code=400)
+
+    def test_same_user_overlap_in_all_directions_is_rejected(self):
+        self.record("09:00", "10:00")
+        for start, end in (("09:00", "10:00"), ("08:30", "09:30"), ("09:30", "10:30"),
+                           ("09:15", "09:45"), ("08:00", "11:00")):
+            with self.subTest(start=start, end=end):
+                self.assertEqual(self.record(start, end).status_code, 400)
+        self.assertEqual(TaskWorkSession.objects.count(), 1)
+        self.task.refresh_from_db()
+        self.assertEqual(self.task.accumulated_hours, Decimal("1.00"))
+
+    def test_adjacent_sessions_before_and_after_are_allowed(self):
+        self.record("09:00", "10:00")
+        self.assertEqual(self.record("08:00", "09:00").status_code, 302)
+        self.assertEqual(self.record("10:00", "11:00").status_code, 302)
+
+    def test_overlap_is_checked_across_tasks(self):
+        self.record()
+        other_task = Task.objects.create(title="Another task", sprint=self.sprint, assignee=self.user)
+        response = self.client.post(reverse("backlog:record_task_time", args=[other_task.pk]),
+                                    self.payload("09:30", "10:30"))
+        self.assertEqual(response.status_code, 400)
+        self.assertFalse(other_task.work_sessions.exists())
+
+    def test_cross_midnight_overlap_is_rejected(self):
+        self.record("23:00", "01:00", end_date="2026-10-01")
+        self.assertEqual(self.record("00:30", "02:00", start_date="2026-10-01",
+                                     end_date="2026-10-01").status_code, 400)
+
+    def test_each_member_has_individual_history_and_combined_task_total(self):
+        self.record()
+        self.task.assignee = self.other
+        self.task.save(update_fields=["assignee"])
+        self.client.force_login(self.other)
+        # Different users may work concurrently.
+        self.assertEqual(self.record("09:00", "11:00").status_code, 302)
+        self.task.refresh_from_db()
+        self.assertEqual(self.task.accumulated_hours, Decimal("3.00"))
+        response = self.client.get(reverse("backlog:task_detail", args=[self.task.pk]))
+        self.assertEqual(list(response.context["time_entries"].values_list("user_id", flat=True)), [self.other.pk])
+        self.assertContains(response, "Logged 2h 00m")
+        self.assertNotContains(response, "Logged 1h 00m")
+        self.assertFalse(TaskHistory.objects.filter(task=self.task).exists())
+
+    def test_total_is_shown_in_all_board_columns_and_board_api(self):
+        self.record("09:00", "10:30")
+        for status in ("not_started", "in_progress", "completed"):
+            with self.subTest(status=status):
+                self.task.status = status
+                self.task.save(update_fields=["status"])
+                response = self.client.get(reverse("backlog:sprint_board_detail", args=[self.sprint.pk]))
+                self.assertContains(response, "Total time: 1h 30m")
+        response = self.client.get(reverse("backlog:sprint_board_data", args=[self.sprint.pk]))
+        self.assertEqual(response.json()["tasks"][0]["accumulated_hours"], "1.50")
+
+    def test_product_backlog_does_not_show_time_information(self):
+        self.record("09:00", "10:30")
+        response = self.client.get(reverse("backlog:product_backlog"))
+        for text in ("Total time:", "Time Tracking", "1h 30m", "Logged 1h"):
+            self.assertNotContains(response, text)
+        self.task.sprint = None
+        self.task.save(update_fields=["sprint"])
+        response = self.client.get(reverse("backlog:task_detail", args=[self.task.pk]))
+        self.assertNotContains(response, "Time Tracking")
+        self.assertNotContains(response, 'id="recordTimeModal"')
+
+    def test_completed_task_rejects_new_and_edited_entries(self):
+        self.record()
+        session = TaskWorkSession.objects.get()
+        self.task.status = "completed"
+        self.task.save(update_fields=["status"])
+        self.assertEqual(self.record("10:00", "11:00").status_code, 400)
+        self.assertEqual(self.client.post(self.edit_url(session), self.payload("09:00", "11:00")).status_code, 400)
+        session.refresh_from_db()
+        self.assertEqual(session.duration, timedelta(hours=1))
+        response = self.client.get(reverse("backlog:task_detail", args=[self.task.pk]))
+        self.assertNotContains(response, 'data-bs-target="#recordTimeModal"')
+        self.assertNotContains(response, 'data-bs-target="#editTimeModal"')
+        self.assertContains(response, "Logged 1h 00m")
+
+    def test_non_active_sprints_reject_create_and_edit(self):
+        self.record()
+        session = TaskWorkSession.objects.get()
+        for status in ("not_started", "planning", "completed"):
+            with self.subTest(status=status):
+                self.sprint.status = status
+                self.sprint.save()
+                self.assertEqual(self.record("10:00", "11:00").status_code, 400)
+                self.assertEqual(self.client.post(self.edit_url(session), self.payload()).status_code, 400)
+        self.assertEqual(TaskWorkSession.objects.count(), 1)
+
+    def test_backlog_deleted_and_missing_tasks_reject_entries(self):
+        self.task.sprint = None
+        self.task.save()
+        self.assertEqual(self.record().status_code, 400)
+        self.task.is_deleted = True
+        self.task.save()
+        self.assertEqual(self.record().status_code, 404)
+        self.assertEqual(self.client.post(reverse("backlog:record_task_time", args=[999999]), self.payload()).status_code, 404)
+
+    def test_edit_updates_existing_session_and_total_instead_of_adding(self):
+        self.record()
+        session = TaskWorkSession.objects.get()
+        response = self.client.post(self.edit_url(session), self.payload("09:00", "11:30"))
+        self.assertEqual(response.status_code, 302)
+        session.refresh_from_db()
+        self.task.refresh_from_db()
+        self.assertEqual(TaskWorkSession.objects.count(), 1)
+        self.assertEqual(session.duration, timedelta(minutes=150))
+        self.assertEqual(self.task.accumulated_hours, Decimal("2.50"))
+        # Saving the identical interval should not overlap itself.
+        self.assertEqual(self.client.post(self.edit_url(session), self.payload("09:00", "11:30")).status_code, 302)
+
+    def test_edit_cannot_overlap_another_session(self):
+        self.record("09:00", "10:00")
+        session = TaskWorkSession.objects.get()
+        self.record("10:00", "11:00")
+        response = self.client.post(self.edit_url(session), self.payload("09:00", "10:30"))
+        self.assertContains(response, "overlaps another", status_code=400)
+        self.assertContains(response, 'data-open-time-modal="editTimeModal"', status_code=400)
+        session.refresh_from_db()
+        self.assertEqual(session.duration, timedelta(hours=1))
+
+    def test_other_members_cannot_edit_someone_elses_entry(self):
+        self.record()
+        session = TaskWorkSession.objects.get()
+        self.task.assignee = self.other
+        self.task.save(update_fields=["assignee"])
+        self.client.force_login(self.other)
+        self.assertEqual(self.client.post(self.edit_url(session), self.payload()).status_code, 404)
+
+    def test_session_cannot_be_edited_through_another_tasks_url(self):
+        self.record()
+        session = TaskWorkSession.objects.get()
+        task = Task.objects.create(title="Other task", sprint=self.sprint, assignee=self.user)
+        url = reverse("backlog:edit_task_time", args=[task.pk, session.pk])
+        self.assertEqual(self.client.post(url, self.payload()).status_code, 404)
+
+    def test_form_has_native_calendar_and_clock_inputs(self):
+        response = self.client.get(reverse("backlog:task_detail", args=[self.task.pk]))
+        self.assertContains(response, 'type="date"', count=4)
+        self.assertContains(response, 'type="time"', count=4)
+        self.assertContains(response, 'name="csrfmiddlewaretoken"')
+        self.assertContains(response, "Asia/Kuala_Lumpur")
+
+    def test_ineligible_user_has_no_record_or_edit_buttons(self):
+        self.client.force_login(self.other)
+        response = self.client.get(reverse("backlog:task_detail", args=[self.task.pk]))
+        self.assertNotContains(response, 'id="recordTimeModal"')
+        self.assertNotContains(response, 'id="editTimeModal"')
+        self.assertContains(response, "Only a Sprint member assigned")
+
+    def test_total_cannot_be_set_through_backlog_forms(self):
+        self.assertNotIn("accumulated_hours", TaskCreateForm().fields)
+        self.assertNotIn("accumulated_hours", TaskEditForm(instance=self.task).fields)
+        self.record()
+        tag = Tag.objects.create(name="US19")
+        response = self.client.post(reverse("backlog:edit_task", args=[self.task.pk]), {
+            "title": self.task.title, "description": "Updated description", "item_type": "story",
+            "story_points": 3, "tags": [tag.pk], "priority": "medium", "assignee": self.user.pk,
+            "status": "not_started", "stage": "planning", "accumulated_hours": "9999",
+        })
+        self.assertEqual(response.status_code, 302)
+        self.task.refresh_from_db()
+        self.assertEqual(self.task.accumulated_hours, Decimal("1.00"))
+
+    def test_too_large_total_rolls_back_entire_submission(self):
+        self.task.accumulated_hours = Decimal("9999.00")
+        self.task.save()
+        self.assertEqual(self.record("09:00", "11:00").status_code, 400)
+        self.assertFalse(TaskWorkSession.objects.exists())
+        self.task.refresh_from_db()
+        self.assertEqual(self.task.accumulated_hours, Decimal("9999.00"))
+
+    def test_database_rejects_non_positive_duration(self):
+        now = timezone.now()
+        with self.assertRaises(IntegrityError), transaction.atomic():
+            TaskWorkSession.objects.create(task=self.task, user=self.user, started_at=now, ended_at=now)
+
+    def test_dst_ambiguous_time_is_rejected(self):
+        with timezone.override("America/New_York"):
+            form = WorkSessionForm(self.payload("01:30", "03:30", start_date="2026-11-01", end_date="2026-11-01"))
+            self.assertFalse(form.is_valid())
```

## 总结

原先只有界面示例，现已接上真实工时记录、后端权限与重叠校验、个人历史、编辑和看板汇总；新增表的本地迁移与全部 147 项测试已完成。
