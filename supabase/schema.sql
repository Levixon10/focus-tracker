-- Run once in Supabase: SQL Editor -> New query -> paste -> Run.
-- Each row belongs to the logged-in user (user_id defaults to auth.uid()),
-- and row-level security makes sure nobody else can read or write it.

create table if not exists public.sessions (
    id          bigint generated always as identity primary key,
    user_id     uuid not null default auth.uid() references auth.users(id) on delete cascade,
    subject     text not null,
    started_at  timestamptz not null,
    ended_at    timestamptz,
    device      text not null,
    unique (user_id, device, started_at)
);

create table if not exists public.activity (
    id        bigint generated always as identity primary key,
    user_id   uuid not null default auth.uid() references auth.users(id) on delete cascade,
    minute    timestamptz not null,
    device    text not null,
    category  text not null,
    subject   text not null default '',
    app       text not null,
    title     text not null default '',
    seconds   double precision not null default 0,
    unique (user_id, minute, device, category, subject, app)
);

create index if not exists activity_user_minute on public.activity (user_id, minute);
create index if not exists sessions_user_started on public.sessions (user_id, started_at);

alter table public.sessions enable row level security;
alter table public.activity enable row level security;

drop policy if exists "own sessions" on public.sessions;
create policy "own sessions" on public.sessions
    for all to authenticated
    using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "own activity" on public.activity;
create policy "own activity" on public.activity
    for all to authenticated
    using (user_id = auth.uid()) with check (user_id = auth.uid());
