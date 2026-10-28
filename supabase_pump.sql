-- MVP pessoal, instalação privada, uma única instância lógica do radar.
-- Execute no SQL Editor do seu Supabase. Não altera crypto_games.
create table if not exists public.pump_radar_state (
    id text primary key check (id = 'main'),
    payload jsonb not null,
    lease_owner uuid,
    lease_until timestamptz not null default '-infinity',
    updated_at timestamptz not null default now()
);
insert into public.pump_radar_state(id,payload) values
('main','{"tokens":{},"alerts":[],"run":{},"backoff_until":0,"version":1}')
on conflict (id) do nothing;
alter table public.pump_radar_state enable row level security;
revoke all on public.pump_radar_state from anon, authenticated;
grant select,update on public.pump_radar_state to service_role;

create or replace function public.pump_acquire(p_owner uuid) returns boolean
language plpgsql security invoker set search_path=public as $$
begin
    update public.pump_radar_state
    set lease_owner=p_owner,lease_until=clock_timestamp()+interval '120 seconds'
    where id='main' and (lease_until<clock_timestamp() or lease_owner=p_owner);
    return found;
end; $$;

create or replace function public.pump_commit(p_owner uuid,p_payload jsonb) returns boolean
language plpgsql security invoker set search_path=public as $$
begin
    update public.pump_radar_state
    set payload=p_payload, updated_at=clock_timestamp(),lease_until=clock_timestamp()+interval '120 seconds'
    where id='main' and lease_owner=p_owner and lease_until>clock_timestamp();
    return found;
end; $$;

create or replace function public.pump_release(p_owner uuid) returns boolean
language plpgsql security invoker set search_path=public as $$
begin
    update public.pump_radar_state set lease_owner=null,lease_until='-infinity'
    where id='main' and lease_owner=p_owner;
    return found;
end; $$;
revoke all on function public.pump_acquire(uuid) from public,anon,authenticated;
revoke all on function public.pump_commit(uuid,jsonb) from public,anon,authenticated;
revoke all on function public.pump_release(uuid) from public,anon,authenticated;
grant execute on function public.pump_acquire(uuid) to service_role;
grant execute on function public.pump_commit(uuid,jsonb) to service_role;
grant execute on function public.pump_release(uuid) to service_role;
