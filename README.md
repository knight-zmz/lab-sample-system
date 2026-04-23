# Lab Sample System

实验室样本管理系统（学习型重构版）。

当前版本基于 **Streamlit + SQLite**，在保留原有业务主线（登记、借用、归还、移位、废弃、项目管理、历史追踪）的基础上，增加了：

- 登录认证
- 基于角色的权限分级（admin / staff / viewer）
- 系统审计日志（与业务流水区分）
- Linux 服务器部署适配（Nginx 反向代理）

## 技术栈

- Python 3.10+
- Streamlit
- SQLite
- Pandas

## 系统数据模型（核心）

- `samples`：样本当前状态
- `borrow_records`：借用单据
- `sample_transactions`：业务流水（CREATE/BORROW/RETURN/MOVE/DISPOSE）
- `audit_logs`：系统审计日志（登录、权限拒绝、管理操作、异常等）

注意：`sample_transactions` 是业务事实，`audit_logs` 是系统行为日志，两者不互相替代。

## 目录说明（关键）

- `app_stable.py`：主入口和页面路由
- `db.py`：统一数据访问层（SQLite）
- `db_init.py`：SQLite 初始化与种子数据
- `auth.py` / `permissions.py`：认证与权限
- `audit.py`：系统审计日志写入
- `services/`：业务服务层（原存储过程逻辑迁移）
- `views/`：页面模块
- `sql/init_sqlite.sql`：SQLite 建表与视图脚本
- `scripts/init_db.py`：初始化数据库脚本

## 初始化与运行

### 1) 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2) 初始化 SQLite

```bash
python scripts/init_db.py
```

可执行冒烟验收（推荐）：

```bash
python scripts/smoke_check.py
```

默认数据库文件位置：

- `data/lab_sample.db`

可通过环境变量自定义：

```bash
export APP_DB_PATH=/home/admin/lab-sample-system/data/lab_sample.db
```

### 3) 默认管理员初始化

初始化脚本会自动创建默认管理员：

- 用户名：`admin`（可通过 `APP_DEFAULT_ADMIN_USER` 覆盖）
- 密码：`admin123`（可通过 `APP_DEFAULT_ADMIN_PASSWORD` 覆盖）

示例：

```bash
export APP_DEFAULT_ADMIN_USER=admin
export APP_DEFAULT_ADMIN_PASSWORD='StrongPass123'
python scripts/init_db.py
```

同时会写入演示用户：

- `admin / admin123`
- `staff / staff123`
- `viewer / viewer123`

上述默认账号仅用于学习和本地演示，不建议在公开环境长期保留默认密码。

### 4) 启动应用

```bash
streamlit run app_stable.py --server.address 0.0.0.0 --server.port 8501
```

若未激活虚拟环境，可直接使用：

```bash
./.venv/bin/streamlit run app_stable.py --server.address 0.0.0.0 --server.port 8501
```

## 角色权限

- `admin`：用户管理、项目管理、样本全操作、记录查看、审计日志查看
- `staff`：样本登记/借用/归还/移位/废弃、样本与记录查看、项目只读
- `viewer`：只读查看样本、项目、记录

## 安全注意（学习项目也建议遵守）

- 不要把数据库令牌、第三方 API 密钥、私钥等敏感信息写入代码仓库。
- 默认账号密码仅用于教学，请在首次登录后修改。
- 服务器部署建议通过环境变量注入配置，避免把真实密码硬编码到脚本与服务文件中。
- 如果项目后续公开，请再次检查 `README`、`deploy`、日志与历史提交，确认无敏感信息泄露。

## Nginx 反向代理建议

优先建议使用子路径 `/lab-sample/`（便于与现有站点共存）。

参考配置见：

- `deploy/nginx-lab-sample.conf.example`

如果子路径与现有站点冲突，可改用独立子域或根路径。

## systemd 启动建议

参考服务文件：

- `deploy/lab-sample.service.example`

常用命令示例：

```bash
sudo cp deploy/lab-sample.service.example /etc/systemd/system/lab-sample.service
sudo systemctl daemon-reload
sudo systemctl enable --now lab-sample
sudo systemctl status lab-sample
```

## 与旧版本差异说明

- 已从 MySQL/PyMySQL 迁移到 SQLite。
- 原 `sp_*` 存储过程逻辑迁移到 Python 服务层，页面调用接口保持一致语义。
- Railway 部署方式不再作为主推荐路径。
- 旧文件 `Railway.session.sql` 仍保留为历史参考，不作为当前运行脚本。
