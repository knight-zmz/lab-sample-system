-- ============================================================================
-- 实验室样本管理数据库系统（重构版）
-- 适用环境：MySQL 8.0+
--
-- 这份脚本对应的设计目标不是“堆砌数据库功能”，而是：
-- 1. 业务主线保持简单：样本登记、借用、归还、移位、废弃。
-- 2. 数据库机制分工清楚：
--    - 表：保存核心数据
--    - 约束：保证数据合法
--    - 索引：优化查询性能
--    - 视图：提供查询抽象
--    - 存储过程：封装核心业务
--    - 函数：提供统计能力
--    - 触发器：只做辅助自动化，不介入核心业务流水
-- 3. 避免旧版本中的逻辑冲突：
--    - 不再让触发器和存储过程同时写业务流水
--    - 不再让初始化数据与触发器重复生成记录
--    - 当前状态与历史流水明确分层
--
-- 重要设计原则：
-- “关键业务动作必须通过存储过程执行”，这样才能保证：
-- 事务完整、逻辑集中、行为可解释、后续易扩展。
-- ============================================================================

-- ============================================================================
-- 0. 数据库初始化
-- ----------------------------------------------------------------------------
-- 说明：
-- 为了让这份脚本可以反复执行，直接采用“删库重建”的方式。
-- 在课程设计和学习阶段，这种方式最清晰；在真实生产环境中通常不会这么做。
-- ============================================================================
DROP DATABASE IF EXISTS lab_sample_db;
CREATE DATABASE lab_sample_db CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE lab_sample_db;


-- ============================================================================
-- 1. 基础主数据表
-- ----------------------------------------------------------------------------
-- 这一部分定义系统中相对稳定、被频繁引用的“主数据”：
-- 用户、样本类型、存储位置、科研项目。
-- 这些表本身不承载复杂流程，而是为后续样本业务提供结构化参照。
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1.1 用户表 users
-- ----------------------------------------------------------------------------
-- 设计说明：
-- 1. username 与 real_name 分离：
--    - username 是系统身份，用于唯一识别、登录名、后续权限扩展。
--    - real_name 是现实身份，用于报表、借用记录展示。
-- 2. 这体现了数据库建模中的一个重要思想：
--    “系统标识”与“现实展示字段”通常不是同一件事。
-- 3. role 暂时只是业务角色字段，不等价于数据库账号权限系统。
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    user_id      INT PRIMARY KEY AUTO_INCREMENT COMMENT '用户主键',
    username     VARCHAR(80)  NOT NULL COMMENT '系统用户名，唯一，用于系统身份识别',
    real_name    VARCHAR(100) NOT NULL COMMENT '真实姓名，用于业务展示',
    role         ENUM('管理员', '实验员', '访客') NOT NULL DEFAULT '实验员' COMMENT '业务角色，不是数据库底层账号权限',
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',

    CONSTRAINT uk_users_username UNIQUE (username)
) COMMENT='系统用户表：保存系统身份与业务展示身份';


-- ----------------------------------------------------------------------------
-- 1.2 样本类型表 sample_types
-- ----------------------------------------------------------------------------
-- 设计说明：
-- 用于管理样本分类。独立成表，而不是直接把类型写死在样本表中，
-- 这样更能体现关系数据库的规范化思想，也更利于后续统计。
-- ----------------------------------------------------------------------------
CREATE TABLE sample_types (
    type_id       INT PRIMARY KEY AUTO_INCREMENT COMMENT '样本类型主键',
    type_name     VARCHAR(100) NOT NULL COMMENT '样本类型名称',
    description   TEXT COMMENT '类型说明',

    CONSTRAINT uk_sample_types_name UNIQUE (type_name)
) COMMENT='样本类型表';


-- ----------------------------------------------------------------------------
-- 1.3 存储位置表 storage_locations
-- ----------------------------------------------------------------------------
-- 设计说明：
-- 样本位置是一个独立业务概念：
-- “借出”与“移位”不是一回事。
-- 因此位置必须成为独立实体，而不是只在备注里写文字。
-- ----------------------------------------------------------------------------
CREATE TABLE storage_locations (
    location_id     INT PRIMARY KEY AUTO_INCREMENT COMMENT '位置主键',
    location_name   VARCHAR(100) NOT NULL COMMENT '位置名称，例如 -80冰柜A-2层',
    description     TEXT COMMENT '位置说明',

    CONSTRAINT uk_storage_locations_name UNIQUE (location_name)
) COMMENT='样本存储位置表';


-- ----------------------------------------------------------------------------
-- 1.4 科研项目表 projects
-- ----------------------------------------------------------------------------
-- 设计说明：
-- 项目不是必须业务，但它是一个很好的“低冲突扩展点”：
-- 1. 能体现多表关联
-- 2. 能支持项目维度统计
-- 3. 不会把主业务流程复杂化
-- ----------------------------------------------------------------------------
CREATE TABLE projects (
    project_id             INT PRIMARY KEY AUTO_INCREMENT COMMENT '项目主键',
    project_name           VARCHAR(120) NOT NULL COMMENT '项目名称',
    principal_investigator VARCHAR(100) COMMENT '项目负责人',
    start_date             DATE COMMENT '项目开始日期',
    end_date               DATE COMMENT '项目结束日期',
    description            TEXT COMMENT '项目说明',

    CONSTRAINT uk_projects_name UNIQUE (project_name),
    CONSTRAINT chk_projects_date CHECK (
        (start_date IS NULL AND end_date IS NULL)
        OR (start_date IS NOT NULL AND end_date IS NULL)
        OR (start_date IS NOT NULL AND end_date IS NOT NULL AND end_date >= start_date)
    )
) COMMENT='科研项目表';


-- ============================================================================
-- 2. 核心业务表
-- ----------------------------------------------------------------------------
-- 这一部分是系统主线：
-- 1. samples 保存样本“当前状态”
-- 2. borrow_records 保存“借用单据”
-- 3. sample_transactions 保存“历史流水”
--
-- 这三层故意分开，是为了避免“谁才是真相来源”混乱：
-- - 当前状态看 samples
-- - 借用过程看 borrow_records
-- - 历史追踪看 sample_transactions
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 2.1 样本表 samples
-- ----------------------------------------------------------------------------
-- 设计说明：
-- 1. 该表只负责保存“当前状态”，不负责保存完整历史。
-- 2. status 采用有限枚举值，而不是随意字符串，目的是体现约束能力。
-- 3. sample_code 是面向业务的样本编号，便于老师和自己理解“业务键”的意义。
-- 4. disposed 表示样本已废弃，此后不允许再借用。
-- ----------------------------------------------------------------------------
CREATE TABLE samples (
    sample_id         INT PRIMARY KEY AUTO_INCREMENT COMMENT '样本主键',
    sample_code       VARCHAR(50) NOT NULL COMMENT '样本编号，业务上用于快速定位样本',
    sample_name       VARCHAR(120) NOT NULL COMMENT '样本名称',
    type_id           INT NOT NULL COMMENT '样本类型外键',
    project_id        INT NULL COMMENT '所属项目外键，可为空，表示暂未关联项目',
    location_id       INT NOT NULL COMMENT '当前存储位置外键',
    status            ENUM('available', 'borrowed', 'disposed') NOT NULL DEFAULT 'available' COMMENT '当前状态：在库/借出/废弃',
    collected_date    DATE COMMENT '采集日期',
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '登记时间',

    CONSTRAINT uk_samples_code UNIQUE (sample_code),
    CONSTRAINT fk_samples_type FOREIGN KEY (type_id) REFERENCES sample_types(type_id),
    CONSTRAINT fk_samples_project FOREIGN KEY (project_id) REFERENCES projects(project_id),
    CONSTRAINT fk_samples_location FOREIGN KEY (location_id) REFERENCES storage_locations(location_id)
) COMMENT='样本表：保存样本当前状态，是当前真相表';


-- ----------------------------------------------------------------------------
-- 2.2 借用记录表 borrow_records
-- ----------------------------------------------------------------------------
-- 设计说明：
-- 1. 一条记录代表一次“借用单据”，而不是所有出入库历史。
-- 2. 这张表只负责借用这件事，不和普通移位、废弃等动作混用。
-- 3. 这样可以清楚区分：
--    - borrowed：样本被人借走
--    - move：样本仍在库，只是位置变化
-- ----------------------------------------------------------------------------
CREATE TABLE borrow_records (
    borrow_id               INT PRIMARY KEY AUTO_INCREMENT COMMENT '借用记录主键',
    sample_id               INT NOT NULL COMMENT '被借样本',
    user_id                 INT NOT NULL COMMENT '借用人',
    borrow_time             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '借出时间',
    expected_return_time    DATETIME NULL COMMENT '预计归还时间',
    actual_return_time      DATETIME NULL COMMENT '实际归还时间',
    status                  ENUM('borrowed', 'returned', 'overdue') NOT NULL DEFAULT 'borrowed' COMMENT '借用状态',
    purpose                 VARCHAR(255) NULL COMMENT '借用用途',
    note                    TEXT NULL COMMENT '备注',

    CONSTRAINT fk_borrow_records_sample FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
    CONSTRAINT fk_borrow_records_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT chk_borrow_records_time CHECK (
        actual_return_time IS NULL OR actual_return_time >= borrow_time
    )
) COMMENT='借用记录表：只保存借还单据，不直接替代样本当前状态';


-- ----------------------------------------------------------------------------
-- 2.3 样本历史流水表 sample_transactions
-- ----------------------------------------------------------------------------
-- 设计说明：
-- 1. 该表记录关键历史动作，是审计/追踪/回顾的基础。
-- 2. 它不负责判断“当前是否可借”，当前状态由 samples 决定。
-- 3. action_type 只保留少量、清晰、与本系统主线吻合的动作类型。
-- ----------------------------------------------------------------------------
CREATE TABLE sample_transactions (
    transaction_id      INT PRIMARY KEY AUTO_INCREMENT COMMENT '流水主键',
    sample_id           INT NOT NULL COMMENT '相关样本',
    user_id             INT NULL COMMENT '操作人，可为空（例如初始化导入）',
    action_type         ENUM('CREATE', 'BORROW', 'RETURN', 'MOVE', 'DISPOSE') NOT NULL COMMENT '动作类型',
    from_location_id    INT NULL COMMENT '变更前位置，仅 MOVE 时常用',
    to_location_id      INT NULL COMMENT '变更后位置，仅 CREATE/MOVE/RETURN 时常用',
    action_time         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '动作发生时间',
    remark              VARCHAR(255) NULL COMMENT '备注',

    CONSTRAINT fk_sample_transactions_sample FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
    CONSTRAINT fk_sample_transactions_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_sample_transactions_from_location FOREIGN KEY (from_location_id) REFERENCES storage_locations(location_id),
    CONSTRAINT fk_sample_transactions_to_location FOREIGN KEY (to_location_id) REFERENCES storage_locations(location_id)
) COMMENT='样本历史流水表：只记录历史，不承担当前状态判断';


-- ============================================================================
-- 3. 索引设计
-- ----------------------------------------------------------------------------
-- 索引不是为了“好看”，而是为了说明数据库如何针对高频查询优化。
-- 这里优先为以下场景建索引：
-- 1. 通过样本编号快速定位样本
-- 2. 按样本类型、位置、项目统计/查询
-- 3. 查询当前借用记录与借用历史
-- 4. 查询流水历史
-- ============================================================================
CREATE INDEX idx_samples_type_id               ON samples(type_id);
CREATE INDEX idx_samples_project_id            ON samples(project_id);
CREATE INDEX idx_samples_location_id           ON samples(location_id);
CREATE INDEX idx_samples_status                ON samples(status);

CREATE INDEX idx_borrow_records_sample_id      ON borrow_records(sample_id);
CREATE INDEX idx_borrow_records_user_id        ON borrow_records(user_id);
CREATE INDEX idx_borrow_records_status         ON borrow_records(status);
CREATE INDEX idx_borrow_records_borrow_time    ON borrow_records(borrow_time);

CREATE INDEX idx_transactions_sample_id        ON sample_transactions(sample_id);
CREATE INDEX idx_transactions_user_id          ON sample_transactions(user_id);
CREATE INDEX idx_transactions_action_type      ON sample_transactions(action_type);
CREATE INDEX idx_transactions_action_time      ON sample_transactions(action_time);


-- ============================================================================
-- 4. 视图设计
-- ----------------------------------------------------------------------------
-- 视图用于“封装常见查询”，而不是替代基础表。
-- 它的价值在于：
-- 1. 降低重复 SQL 编写
-- 2. 让查询结果更接近业务语言
-- 3. 为未来只读权限控制预留接口
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 4.1 样本详情视图
-- ----------------------------------------------------------------------------
-- 用途：
-- 把样本表、类型表、位置表、项目表进行整合，形成最常见的“综合查询视图”。
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_sample_detail AS
SELECT
    s.sample_id,
    s.sample_code,
    s.sample_name,
    st.type_name,
    p.project_name,
    sl.location_name,
    s.status,
    s.collected_date,
    s.created_at
FROM samples s
JOIN sample_types st
    ON s.type_id = st.type_id
LEFT JOIN projects p
    ON s.project_id = p.project_id
JOIN storage_locations sl
    ON s.location_id = sl.location_id;


-- ----------------------------------------------------------------------------
-- 4.2 当前借用样本视图
-- ----------------------------------------------------------------------------
-- 用途：
-- 直接给出“当前有哪些样本正在被借用”，这是一个典型业务查询。
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_current_borrowed_samples AS
SELECT
    br.borrow_id,
    s.sample_id,
    s.sample_code,
    s.sample_name,
    u.real_name AS borrower_name,
    br.borrow_time,
    br.expected_return_time,
    br.status,
    br.purpose,
    br.note
FROM borrow_records br
JOIN samples s
    ON br.sample_id = s.sample_id
JOIN users u
    ON br.user_id = u.user_id
WHERE br.status IN ('borrowed', 'overdue');


-- ----------------------------------------------------------------------------
-- 4.3 样本类型统计视图
-- ----------------------------------------------------------------------------
-- 用途：
-- 展示聚合统计能力，便于按类型查看样本规模。
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_sample_statistics_by_type AS
SELECT
    st.type_id,
    st.type_name,
    COUNT(s.sample_id) AS sample_count
FROM sample_types st
LEFT JOIN samples s
    ON st.type_id = s.type_id
GROUP BY st.type_id, st.type_name;


-- ----------------------------------------------------------------------------
-- 4.4 项目维度样本统计视图
-- ----------------------------------------------------------------------------
-- 用途：
-- 体现项目作为扩展维度时的统计价值。
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_project_sample_statistics AS
SELECT
    p.project_id,
    p.project_name,
    COUNT(s.sample_id) AS sample_count
FROM projects p
LEFT JOIN samples s
    ON p.project_id = s.project_id
GROUP BY p.project_id, p.project_name;




DROP FUNCTION IF EXISTS fn_sample_count_by_type;
DROP FUNCTION IF EXISTS fn_active_borrow_count_by_user;

DELIMITER $$


RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_count INT;

    SELECT COUNT(*)
      INTO v_count
      FROM samples
     WHERE type_id = p_type_id;

    RETURN v_count;
END $$



CREATE FUNCTION fn_active_borrow_count_by_user(p_user_id INT)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_count INT;

    SELECT COUNT(*)
      INTO v_count
      FROM borrow_records
     WHERE user_id = p_user_id
       AND status IN ('borrowed', 'overdue');

    RETURN v_count;
END $$

DELIMITER ;




DROP TRIGGER IF EXISTS trg_users_normalize_username_before_insert;
DROP TRIGGER IF EXISTS trg_users_normalize_username_before_update;
DROP TRIGGER IF EXISTS trg_samples_validate_collected_date_before_insert;
DROP TRIGGER IF EXISTS trg_samples_validate_collected_date_before_update;

DELIMITER $$


CREATE TRIGGER trg_users_normalize_username_before_insert
BEFORE INSERT ON users
FOR EACH ROW
BEGIN
    SET NEW.username = LOWER(TRIM(NEW.username));
END $$



CREATE TRIGGER trg_users_normalize_username_before_update
BEFORE UPDATE ON users
FOR EACH ROW
BEGIN
    SET NEW.username = LOWER(TRIM(NEW.username));
END $$



CREATE TRIGGER trg_samples_validate_collected_date_before_insert
BEFORE INSERT ON samples
FOR EACH ROW
BEGIN
    IF NEW.collected_date IS NOT NULL AND NEW.collected_date > CURDATE() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '采集日期不能晚于当前日期';
    END IF;
END $$



CREATE TRIGGER trg_samples_validate_collected_date_before_update
BEFORE UPDATE ON samples
FOR EACH ROW
BEGIN
    IF NEW.collected_date IS NOT NULL AND NEW.collected_date > CURDATE() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '采集日期不能晚于当前日期';
    END IF;
END $$

DELIMITER ;




DROP PROCEDURE IF EXISTS sp_register_sample;
DROP PROCEDURE IF EXISTS sp_borrow_sample;
DROP PROCEDURE IF EXISTS sp_return_sample;
DROP PROCEDURE IF EXISTS sp_move_sample;
DROP PROCEDURE IF EXISTS sp_dispose_sample;

DELIMITER $$


CREATE PROCEDURE sp_register_sample(
    IN p_sample_name        VARCHAR(120),
    IN p_type_id            INT,
    IN p_project_id         INT,
    IN p_location_id        INT,
    IN p_collected_date     DATE,
    IN p_user_id            INT,
    IN p_remark             VARCHAR(255)
)
BEGIN
    DECLARE v_sample_id INT;
    DECLARE v_sample_code VARCHAR(50);

    START TRANSACTION;

    -- 基础存在性检查
    IF NOT EXISTS (SELECT 1 FROM sample_types WHERE type_id = p_type_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '样本类型不存在';
    END IF;

    IF p_project_id IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM projects WHERE project_id = p_project_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '所属项目不存在';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM storage_locations WHERE location_id = p_location_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '存储位置不存在';
    END IF;

    IF p_user_id IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM users WHERE user_id = p_user_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '登记用户不存在';
    END IF;

    IF p_collected_date IS NOT NULL AND p_collected_date > CURRENT_DATE THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '采集日期不能晚于当前日期';
    END IF;

    INSERT INTO samples (
        sample_code,
        sample_name,
        type_id,
        project_id,
        location_id,
        status,
        collected_date
    ) VALUES (
        CONCAT('PENDING-', DATE_FORMAT(NOW(), '%Y%m%d%H%i%s')),
        p_sample_name,
        p_type_id,
        p_project_id,
        p_location_id,
        'available',
        p_collected_date
    );

    SET v_sample_id = LAST_INSERT_ID();
    SET v_sample_code = CONCAT('S', DATE_FORMAT(CURDATE(), '%Y%m%d'), '-', LPAD(v_sample_id, 4, '0'));

    UPDATE samples
       SET sample_code = v_sample_code
     WHERE sample_id = v_sample_id;

    INSERT INTO sample_transactions (
        sample_id,
        user_id,
        action_type,
        from_location_id,
        to_location_id,
        remark
    ) VALUES (
        v_sample_id,
        p_user_id,
        'CREATE',
        NULL,
        p_location_id,
        COALESCE(p_remark, '样本登记入库')
    );

    COMMIT;
END $$



CREATE PROCEDURE sp_borrow_sample(
    IN p_sample_id                INT,
    IN p_user_id                  INT,
    IN p_expected_return_time     DATETIME,
    IN p_purpose                  VARCHAR(255),
    IN p_note                     TEXT
)
BEGIN
    DECLARE v_status VARCHAR(20);
    DECLARE v_location_id INT;

    START TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM users WHERE user_id = p_user_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '借用用户不存在';
    END IF;

    SELECT status, location_id
      INTO v_status, v_location_id
      FROM samples
     WHERE sample_id = p_sample_id
     FOR UPDATE;

    IF v_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '样本不存在';
    END IF;

    IF v_status = 'borrowed' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '样本当前已借出，不能重复借用';
    END IF;

    IF v_status = 'disposed' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '样本已废弃，不能借用';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM borrow_records
         WHERE sample_id = p_sample_id
           AND status IN ('borrowed', 'overdue')
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '该样本存在未结束的借用记录';
    END IF;

    IF p_expected_return_time IS NOT NULL AND p_expected_return_time <= NOW() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '预计归还时间必须晚于当前时间';
    END IF;

    INSERT INTO borrow_records (
        sample_id,
        user_id,
        borrow_time,
        expected_return_time,
        actual_return_time,
        status,
        purpose,
        note
    ) VALUES (
        p_sample_id,
        p_user_id,
        NOW(),
        p_expected_return_time,
        NULL,
        'borrowed',
        p_purpose,
        p_note
    );

    UPDATE samples
       SET status = 'borrowed'
     WHERE sample_id = p_sample_id;

    INSERT INTO sample_transactions (
        sample_id,
        user_id,
        action_type,
        from_location_id,
        to_location_id,
        remark
    ) VALUES (
        p_sample_id,
        p_user_id,
        'BORROW',
        v_location_id,
        NULL,
        COALESCE(p_note, '样本借出')
    );

    COMMIT;
END $$

CREATE PROCEDURE sp_return_sample(
    IN p_sample_id         INT,
    IN p_user_id           INT,
    IN p_note              TEXT
)
BEGIN
    DECLARE v_status VARCHAR(20);
    DECLARE v_location_id INT;
    DECLARE v_borrow_id INT;

    START TRANSACTION;

    IF p_user_id IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM users WHERE user_id = p_user_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '归还操作用户不存在';
    END IF;

    SELECT status, location_id
      INTO v_status, v_location_id
      FROM samples
     WHERE sample_id = p_sample_id
     FOR UPDATE;

    IF v_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '样本不存在';
    END IF;

    IF v_status <> 'borrowed' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '样本当前并非借出状态，不能执行归还';
    END IF;

    SELECT borrow_id
      INTO v_borrow_id
      FROM borrow_records
     WHERE sample_id = p_sample_id
       AND status IN ('borrowed', 'overdue')
     ORDER BY borrow_time DESC
     LIMIT 1
     FOR UPDATE;

    IF v_borrow_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '未找到有效的借用记录，无法归还';
    END IF;

    UPDATE borrow_records
       SET actual_return_time = NOW(),
           status = 'returned',
           note = CONCAT(COALESCE(note, ''),
                         CASE WHEN note IS NULL OR note = '' THEN '' ELSE '；' END,
                         COALESCE(p_note, '样本已归还'))
     WHERE borrow_id = v_borrow_id;

    UPDATE samples
       SET status = 'available'
     WHERE sample_id = p_sample_id;

    INSERT INTO sample_transactions (
        sample_id,
        user_id,
        action_type,
        from_location_id,
        to_location_id,
        remark
    ) VALUES (
        p_sample_id,
        p_user_id,
        'RETURN',
        NULL,
        v_location_id,
        COALESCE(p_note, '样本归还入库')
    );

    COMMIT;
END $$


CREATE PROCEDURE sp_move_sample(
    IN p_sample_id             INT,
    IN p_new_location_id       INT,
    IN p_user_id               INT,
    IN p_note                  VARCHAR(255)
)
BEGIN
    DECLARE v_status VARCHAR(20);
    DECLARE v_old_location_id INT;

    START TRANSACTION;

    IF p_user_id IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM users WHERE user_id = p_user_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '操作用户不存在';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM storage_locations WHERE location_id = p_new_location_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '新存储位置不存在';
    END IF;

    SELECT status, location_id
      INTO v_status, v_old_location_id
      FROM samples
     WHERE sample_id = p_sample_id
     FOR UPDATE;

    IF v_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '样本不存在';
    END IF;

    IF v_status = 'borrowed' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '样本正在借出中，不能直接移位';
    END IF;

    IF v_status = 'disposed' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '样本已废弃，不能移位';
    END IF;

    IF v_old_location_id = p_new_location_id THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '新旧位置相同，无需移位';
    END IF;

    UPDATE samples
       SET location_id = p_new_location_id
     WHERE sample_id = p_sample_id;

    INSERT INTO sample_transactions (
        sample_id,
        user_id,
        action_type,
        from_location_id,
        to_location_id,
        remark
    ) VALUES (
        p_sample_id,
        p_user_id,
        'MOVE',
        v_old_location_id,
        p_new_location_id,
        COALESCE(p_note, '样本位置调整')
    );

    COMMIT;
END $$



CREATE PROCEDURE sp_dispose_sample(
    IN p_sample_id      INT,
    IN p_user_id        INT,
    IN p_note           VARCHAR(255)
)
BEGIN
    DECLARE v_status VARCHAR(20);
    DECLARE v_location_id INT;

    START TRANSACTION;

    IF p_user_id IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM users WHERE user_id = p_user_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '操作用户不存在';
    END IF;

    SELECT status, location_id
      INTO v_status, v_location_id
      FROM samples
     WHERE sample_id = p_sample_id
     FOR UPDATE;

    IF v_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '样本不存在';
    END IF;

    IF v_status = 'borrowed' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '样本处于借出状态，必须归还后才能废弃';
    END IF;

    IF v_status = 'disposed' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '样本已废弃，无需重复操作';
    END IF;

    UPDATE samples
       SET status = 'disposed'
     WHERE sample_id = p_sample_id;

    INSERT INTO sample_transactions (
        sample_id,
        user_id,
        action_type,
        from_location_id,
        to_location_id,
        remark
    ) VALUES (
        p_sample_id,
        p_user_id,
        'DISPOSE',
        v_location_id,
        NULL,
        COALESCE(p_note, '样本废弃处理')
    );

    COMMIT;
END $$

DELIMITER ;


-- 8.1 用户
INSERT INTO users (username, real_name, role) VALUES
('admin',    '系统管理员', '管理员'),
('zhangsan', '张三',       '实验员'),
('lisi',     '李四',       '实验员'),
('visitor1', '王五',       '访客');

-- 8.2 样本类型
INSERT INTO sample_types (type_name, description) VALUES
('血液样本', '来源于实验对象的血液样本'),
('组织样本', '来源于心脏、肝脏等组织'),
('细胞样本', '培养细胞或细胞提取物');

-- 8.3 存储位置
INSERT INTO storage_locations (location_name, description) VALUES
('冰箱A-1层',   '4℃冰箱第一层'),
('-80冰柜A-2层', '-80℃冰柜第二层'),
('液氮罐1号',    '液氮长期保存区域');

-- 8.4 科研项目
INSERT INTO projects (project_name, principal_investigator, start_date, end_date, description) VALUES
('鹿心多肽活性研究', '王老师', '2026-03-01', NULL, '用于研究鹿心来源样本及相关活性机制'),
('细胞应激实验项目', '李老师', '2026-02-20', NULL, '关注细胞提取物与应激响应');

-- 8.5 通过存储过程登记样本
CALL sp_register_sample('鹿心血清样本A', 1, 1, 2, '2026-03-10', 1, '初始登记');
CALL sp_register_sample('鹿心组织样本B', 2, 1, 2, '2026-03-09', 2, '初始登记');
CALL sp_register_sample('细胞提取物C',   3, 2, 1, '2026-03-08', 3, '初始登记');

-- 8.6 演示部分业务动作
-- 先借出 1 号样本，再移位 2 号样本，最后废弃 3 号样本。
CALL sp_borrow_sample(1, 2, DATE_ADD(NOW(), INTERVAL 3 DAY), '蛋白提取实验', '教学演示：借用样本');
CALL sp_move_sample(2, 3, 1, '教学演示：转移到液氮罐保存');
CALL sp_dispose_sample(3, 1, '教学演示：样本质量不满足保存要求，执行废弃');




-- 查看样本详情
SELECT * FROM v_sample_detail ORDER BY sample_id;

-- 查看当前借用样本
SELECT * FROM v_current_borrowed_samples ORDER BY borrow_time DESC;

-- 查看样本类型统计
SELECT * FROM v_sample_statistics_by_type ORDER BY type_id;

-- 查看项目统计
SELECT * FROM v_project_sample_statistics ORDER BY project_id;

-- 查看历史流水
SELECT
    transaction_id,
    sample_id,
    user_id,
    action_type,
    from_location_id,
    to_location_id,
    action_time,
    remark
FROM sample_transactions
ORDER BY transaction_id;

-- 调用函数：某类型样本数量
SELECT fn_sample_count_by_type(1) AS blood_sample_count;

-- 调用函数：某用户当前借用中的样本数量
SELECT fn_active_borrow_count_by_user(2) AS active_borrow_count_of_user_2;

-- 查看索引优化效果（示例）
EXPLAIN SELECT * FROM samples WHERE type_id = 1;
EXPLAIN SELECT * FROM borrow_records WHERE user_id = 2 AND status IN ('borrowed', 'overdue');


-- ============================================================================
-- 10. 设计总结（写在 SQL 里的学习性备注）
-- ----------------------------------------------------------------------------
-- 这份脚本最重要的不是“功能多”，而是“语义不打架”：
--
-- 1. samples      -> 只管当前状态
-- 2. borrow_records -> 只管借用单据
-- 3. sample_transactions -> 只管历史流水
--
-- 4. 借用、归还、移位、废弃都通过存储过程统一执行
-- 5. 触发器不再参与业务流水写入，避免重复记账
-- 6. 视图和函数分别承担查询抽象与单值统计的角色
--
-- 这就是这份课程设计最核心的数据库思想：
-- “同一个业务动作，最好只有一个主入口；不同数据库机制应各守边界。”
-- ============================================================================
