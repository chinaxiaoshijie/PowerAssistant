-- Create feishu_tasks table
CREATE TABLE IF NOT EXISTS feishu_tasks (
    id SERIAL PRIMARY KEY,
    feishu_task_id VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    priority VARCHAR(20) NOT NULL DEFAULT 'p2',
    due_date DATE,
    completed_at TIMESTAMP,
    assignee_ids JSON NOT NULL DEFAULT '[]',
    reporter_id VARCHAR(100),
    project_id VARCHAR(100),
    parent_task_id VARCHAR(100),
    labels JSON NOT NULL DEFAULT '[]',
    is_tech_debt BOOLEAN NOT NULL DEFAULT FALSE,
    story_points FLOAT,
    actual_hours FLOAT,
    estimated_hours FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sync_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_feishu_tasks_status ON feishu_tasks(status);
CREATE INDEX IF NOT EXISTS ix_feishu_tasks_priority ON feishu_tasks(priority);
CREATE INDEX IF NOT EXISTS ix_feishu_tasks_due_date ON feishu_tasks(due_date);
CREATE INDEX IF NOT EXISTS ix_feishu_tasks_project ON feishu_tasks(project_id);

-- Create feishu_projects table
CREATE TABLE IF NOT EXISTS feishu_projects (
    id SERIAL PRIMARY KEY,
    feishu_project_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'planning',
    start_date DATE,
    end_date DATE,
    actual_end_date DATE,
    owner_id VARCHAR(100),
    member_ids JSON NOT NULL DEFAULT '[]',
    milestones JSON NOT NULL DEFAULT '[]',
    risk_level VARCHAR(20) NOT NULL DEFAULT 'low',
    progress INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sync_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_feishu_projects_status ON feishu_projects(status);
CREATE INDEX IF NOT EXISTS ix_feishu_projects_risk ON feishu_projects(risk_level);

-- Create feishu_okrs table
CREATE TABLE IF NOT EXISTS feishu_okrs (
    id SERIAL PRIMARY KEY,
    feishu_okr_id VARCHAR(100) UNIQUE NOT NULL,
    objective VARCHAR(500) NOT NULL,
    key_results JSON NOT NULL DEFAULT '[]',
    progress INTEGER NOT NULL DEFAULT 0,
    owner_id VARCHAR(100),
    cycle VARCHAR(50) NOT NULL,
    parent_okr_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sync_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_feishu_okrs_cycle ON feishu_okrs(cycle);
CREATE INDEX IF NOT EXISTS ix_feishu_okrs_owner ON feishu_okrs(owner_id);
