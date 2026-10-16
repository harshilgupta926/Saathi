-- Saathi household memory and follow-up foundation.
-- Apply only after reviewing against the target Supabase project.
-- Browser roles receive no access; the trusted backend uses service_role.
-- Do not store raw transcripts or document contents unless necessary and consented.

create extension if not exists pgcrypto;

create table if not exists public.households (
    id uuid primary key default gen_random_uuid(),
    phone_number text unique,
    preferred_language text not null default 'hi',
    dialect_context jsonb not null default '{}'::jsonb,
    memory_consent boolean not null default false,
    memory_consent_at timestamptz,
    outbound_call_consent boolean not null default false,
    outbound_call_consent_at timestamptz,
    consent_revoked_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint household_memory_consent_timestamp check
      (memory_consent = false or memory_consent_at is not null),
    constraint household_call_consent_timestamp check
      (outbound_call_consent = false or outbound_call_consent_at is not null)
);

create table if not exists public.household_memories (
    id uuid primary key default gen_random_uuid(),
    household_id uuid not null references public.households(id) on delete cascade,
    memory_type text not null,
    key_name text not null,
    value_text text not null,
    source text not null default 'user_confirmed',
    updated_at timestamptz not null default now(),
    expires_at timestamptz,
    unique (household_id, memory_type, key_name)
);

create table if not exists public.pending_tasks (
    id uuid primary key default gen_random_uuid(),
    household_id uuid not null references public.households(id) on delete cascade,
    title text not null,
    status text not null default 'pending'
      check (status in ('pending', 'scheduled', 'in_progress', 'completed', 'cancelled', 'escalated', 'failed')),
    missing_requirements text[] not null default '{}',
    scheduled_callback timestamptz,
    timezone_name text not null default 'Asia/Kolkata',
    idempotency_key text not null unique,
    callback_attempts integer not null default 0 check (callback_attempts >= 0),
    last_attempt_at timestamptz,
    completed_at timestamptz,
    cancelled_at timestamptz,
    last_error_code text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists pending_tasks_due_idx
  on public.pending_tasks (scheduled_callback)
  where status in ('pending', 'scheduled');

create table if not exists public.volunteer_cases (
    id uuid primary key default gen_random_uuid(),
    household_id uuid references public.households(id) on delete set null,
    task_id uuid references public.pending_tasks(id) on delete set null,
    status text not null default 'open'
      check (status in ('open', 'assigned', 'in_progress', 'resolved', 'closed')),
    priority text not null default 'normal'
      check (priority in ('low', 'normal', 'high', 'urgent')),
    summary text not null,
    assigned_to text,
    resolution_note text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    resolved_at timestamptz
);

create index if not exists volunteer_cases_open_idx
  on public.volunteer_cases (priority, created_at)
  where status in ('open', 'assigned', 'in_progress');

-- RLS is defense in depth. No client/browser role is granted table access.
alter table public.households enable row level security;
alter table public.household_memories enable row level security;
alter table public.pending_tasks enable row level security;
alter table public.volunteer_cases enable row level security;

revoke all on public.households from anon, authenticated;
revoke all on public.household_memories from anon, authenticated;
revoke all on public.pending_tasks from anon, authenticated;
revoke all on public.volunteer_cases from anon, authenticated;

grant all on public.households to service_role;
grant all on public.household_memories to service_role;
grant all on public.pending_tasks to service_role;
grant all on public.volunteer_cases to service_role;

comment on table public.households is
  'PII-bearing household record. Access only through authenticated trusted backend; collect consent explicitly.';
comment on table public.household_memories is
  'Consent-gated, minimal household facts. Do not store sensitive facts without a documented need.';
comment on table public.pending_tasks is
  'Durable follow-up queue. Dispatcher must re-check current outbound_call_consent, quiet hours and opt-out before every call.';
comment on table public.volunteer_cases is
  'Human-in-the-loop cases. Keep summaries minimal and redact sensitive content.';
