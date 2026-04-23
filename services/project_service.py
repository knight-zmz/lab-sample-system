import sqlite3

from services.sample_service import BusinessError


def create_project(
    conn,
    project_name,
    principal_investigator,
    start_date,
    end_date,
    description,
):
    name = (project_name or "").strip()
    if not name:
        raise BusinessError("请填写项目名称。")
    if end_date is not None and start_date is None:
        raise BusinessError("填写结束日期时，请同时填写开始日期。")

    cursor = conn.execute(
        """
        INSERT INTO projects (project_name, principal_investigator, start_date, end_date, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            name,
            (principal_investigator or "").strip() or None,
            start_date,
            end_date,
            (description or "").strip() or None,
        ),
    )
    return int(cursor.lastrowid)


def update_project(
    conn,
    project_id,
    project_name,
    principal_investigator,
    start_date,
    end_date,
    description,
):
    name = (project_name or "").strip()
    if not name:
        raise BusinessError("请填写项目名称。")
    if end_date is not None and start_date is None:
        raise BusinessError("填写结束日期时，请同时填写开始日期。")

    conn.execute(
        """
        UPDATE projects
        SET project_name = ?, principal_investigator = ?, start_date = ?, end_date = ?, description = ?
        WHERE project_id = ?
        """,
        (
            name,
            (principal_investigator or "").strip() or None,
            start_date,
            end_date,
            (description or "").strip() or None,
            project_id,
        ),
    )


def delete_project(conn, project_id):
    row = conn.execute(
        "SELECT COUNT(*) AS sample_count FROM samples WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    if row and int(row["sample_count"]) > 0:
        raise BusinessError(f"该项目仍关联 {int(row['sample_count'])} 个样本，不能直接删除。")
    conn.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
