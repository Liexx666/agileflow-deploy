# 首次登录与 Backlog 页面改动清单

日期：2026-10-03。分支：`sprint2-yaoxing`。

## 完成的功能

- 首次登录后必须更换初始密码，才能进入 Board、Backlog、账户管理或其他业务页面。
- 改密码要验证旧密码，两次新密码必须一致，并遵守现有密码规则；不能沿用旧密码。
- 改完密码后继续保持登录，并进入 Sprint Board；以后登录不再重复要求修改。
- 管理员将用户密码重置为初始密码后，该用户需要再次修改密码。
- 登录后和主页默认显示当前用户可访问的 Active Sprint Board。
- 没有可访问的 Active Sprint 时显示明确的空状态；可以选择其他 Sprint 或进入 Backlogs。
- 主 Sprint Board 不支持拖动，任务通过状态下拉菜单更新，更新后 Board 和燃尽图重新显示数据库中的进度。
- “Add tasks from Backlog” 和 “View Sprint Backlog” 进入当前 Sprint 的独立 Backlog 管理页面。
- 独立 Backlog 页面同时显示该 Sprint 的任务和 Product Backlog，支持任务拖入 Active Sprint、移回 Product Backlog。
- 全部 Backlog 管理页面支持列表/卡片视图、原有过滤排序，并提供每个 Sprint 的独立 Backlog 入口。
- 从独立 Sprint Backlog 新建任务后，任务先进入 Product Backlog，页面返回原来的 Sprint Backlog，便于继续拖动分配。
- 取消新建任务或点击返回链接，也回到原来的 Backlog 页面。

## 页面入口

| 地址 | 用途 |
|---|---|
| `/` | 登录后的主页，转到 Sprint Board |
| `/password/change/` | 首次登录强制改密码页面 |
| `/sprint-board/` | 当前用户可访问的 Active Sprint Board |
| `/sprint-board/<id>/` | 指定 Sprint 的 Board |
| `/backlog/` | 全部可访问的 Sprint Backlog + Product Backlog 管理页 |
| `/sprints/<id>/backlog/` | 指定 Sprint 的独立 Backlog + Product Backlog 管理页 |
| `/tasks/new/?backlog_sprint=<id>` | 从指定 Sprint Backlog 创建 Product Backlog 任务，并返回同一管理页 |

## 代码文件：新增了什么、原来的代码改成了什么

| 文件 | 类型 | 具体修改 |
|---|---|---|
| `accounts/models.py` | 新增 | `AccountSecurity` 与 User 一对一关联；`must_change_password` 默认 True，用数据库保存强制改密码状态。 |
| `accounts/apps.py` | 新增 | 应用启动时注册用户创建信号。 |
| `accounts/signals.py` | 新增 | 新用户创建后自动生成安全状态，确保管理页面、Django Admin、命令行创建的账号都有首次改密码要求。 |
| `accounts/middleware.py` | 新增 | 每个已登录用户访问业务页面前检查安全状态；未改密码只能进入改密码页面或退出登录。 |
| `accounts/migrations/__init__.py` | 新增 | 创建 accounts 的数据库迁移包。 |
| `accounts/migrations/0001_initial.py` | 新增 | 创建安全状态表；已有账号中，未登录过或仍使用初始 `password123` 的账号被设为必须修改密码。已有用户密码保持原来的哈希值。 |
| `accounts/forms.py` | 修改 | 新增 `InitialPasswordChangeForm`，继承 Django `PasswordChangeForm`；验证旧密码、确认密码、现有复杂度规则和新旧密码不同。 |
| `accounts/views.py` | 修改 | 登录成功后按安全标记决定进入改密码页面或主页；新增 `change_password_ui`；保存新密码与解除标记放在同一事务中；使用 `update_session_auth_hash` 保持当前登录。管理员重置密码时同时重新设置强制修改标记。 |
| `accounts/urls.py` | 修改 | 新增 `password/change/` 路由。 |
| `agileflow_project/settings.py` | 修改 | 在认证与消息中间件之后加入 `RequirePasswordChangeMiddleware`。 |
| `templates/accounts/change_password.html` | 新增 | 显示旧密码、新密码、确认密码、错误提示、继续按钮和退出按钮。 |
| `backlog/views.py` | 修改 | 新增主页 `home`；新增可访问 Sprint 查询函数 `available_sprints`；Backlog 视图接收可选 Sprint id，共用同一套页面；过滤已删除和无权访问的 Sprint；Board 默认选 Active Sprint；计算状态菜单权限；新建任务按来源返回正确页面。任务分组从逐 Sprint 重复扫描改成一次分组。 |
| `backlog/urls.py` | 修改 | `/` 改为主页，原 Product Backlog 改到 `/backlog/`；新增 `/sprints/<id>/backlog/`。 |
| `backlog/sprint_services.py` | 修改 | 拖入 Sprint 的后端查找增加 `is_deleted=False`，防止分配到已删除的 Sprint；继续复用原有成员权限和 Active Sprint 校验。 |
| `templates/base.html` | 修改 | 品牌链接转到主页；新增 Sprint Board 与 Backlogs 导航；强制改密码期间隐藏业务导航和账户功能入口，保留退出；交互脚本增加版本参数。 |
| `templates/backlog/product_backlog.html` | 修改 | 页面改为独立 Backlog 管理用途；可显示全部可访问 Sprint，也可只显示选定 Sprint；新增返回 Board/全部 Backlog 入口；Sprint 名称链接到独立 Backlog；过滤/清除条件保留当前页面；标记合法拖动目标；新建任务携带来源 Sprint。 |
| `templates/backlog/sprint_board.html` | 修改 | 增加 Add tasks 和 View Sprint Backlog 按钮；删除拖动提示和拖动区域；任务卡片使用统一模板；新增没有 Active Sprint 的说明及选择占位项。 |
| `templates/backlog/_board_task.html` | 新增 | 共用任务卡片模板，明确 `draggable="false"`；有权限且 Sprint 为 Active 时显示状态下拉菜单。 |
| `templates/backlog/create_task.html` | 修改 | Back 和 Cancel 链接由固定 Product Backlog 地址改为来源页面地址。 |
| `static/js/backlog.js` | 修改 | 拖动绑定限定在 `data-backlog-manager` 容器内；只绑定有权限的任务和合法放置目标；处理拖入放置区事件，复用已有任务移动接口和 assignee 选择提示。 |
| `static/js/sprint_board.js` | 修改 | 原拖动逻辑替换为状态菜单请求；成功后刷新 Board；失败时恢复原选择；遇到登录跳转时进入相应页面。 |

## 核心逻辑怎么理解

登录次数不等于“是否已经修改过密码”。所以使用独立标记保存这个状态：

```python
must_change_password = models.BooleanField(default=True)
```

用户提交有效的新密码后，在同一次数据库事务中保存密码并清除标记：

```python
with transaction.atomic():
    user = form.save()
    security.must_change_password = False
    security.save(update_fields=["must_change_password"])
update_session_auth_hash(request, user)
```

中间件在业务视图执行前检查这个标记，所以直接输入网址或调用写入接口也不能跳过首次改密码。

主 Board 专注显示任务进度；独立 Backlog 页面专注任务分配。两者使用相同的 Task/Sprint 数据和原有业务接口，拖动后保存的结果会出现在 Board 中。

Backlog 的任务分组使用字典：整理过程约为 `O(任务数 + Sprint 数)`，避免为每个 Sprint 重复扫描所有任务。

## 运行检查结果

没有新增或修改测试文件。使用临时 SQLite 数据库运行应用接口及浏览器检查，临时数据库检查结束后删除。

- 首次登录、直接访问 Board/Backlog/Admin、改密码失败、改密码成功、退出再登录：通过。
- 错误旧密码、重复旧密码、短密码和两次密码不一致：被拒绝。
- 管理员重置后再次强制修改：通过。
- 无权访问其他团队 Sprint、分配到非 Active 或已删除 Sprint：被拒绝。
- 主 Board 默认 Active Sprint、无 Active 时的空页面、状态下拉更新：通过。
- 独立 Backlog 的卡片拖入、列表拖回和列表再次拖入：浏览器操作通过，数据库结果确认。
- 新建任务存入 Product Backlog、记录 TaskHistory 并返回来源 Sprint Backlog：通过。
- Django 系统检查、数据库迁移及模板加载：通过；修改的 JavaScript 语法检查通过。

## 数据库与提交说明

本地数据库已先备份，再执行迁移。备份为 `db.before-login-backlogs-20261003-154138.sqlite3`，数据库及备份受 `.gitignore` 排除。

部署或在其他电脑拉取本次代码后，需要在该环境执行 `python manage.py migrate`，创建新的 accounts 表。

当前改动保留在工作区，未自动执行 commit 或 push。

参考：Django 的改密码表单、会话更新和视图中间件说明：

- [改密码后的会话更新](https://docs.djangoproject.com/en/5.2/topics/auth/default/#session-invalidation-on-password-change)
- [视图执行前的中间件检查](https://docs.djangoproject.com/en/5.2/topics/http/middleware/#process-view)
