-- Reversible per-account experiment. Existing classic screening stays intact.
alter table public.sniper_profiles add column if not exists radar_mode text not null default 'classic'
 check(radar_mode in ('classic','early-v1'));
alter table public.sniper_profiles add column if not exists radar_mode_since timestamptz not null default now();
create table if not exists public.dex_early_trials (
 id uuid primary key,
 first_at timestamptz not null,
 address text not null,
 payload jsonb not null
);
alter table public.dex_early_trials enable row level security;
revoke all on public.dex_early_trials from public,anon,authenticated;
grant select on public.dex_early_trials to authenticated;
grant select,insert,update,delete on public.dex_early_trials to service_role;
create policy early_trial_read on public.dex_early_trials for select to authenticated using ((select public.sniper_active()));
create policy early_trial_service on public.dex_early_trials for all to service_role using(true) with check(true);
create index dex_early_trials_first on public.dex_early_trials(first_at desc,id desc);
create or replace function public.dex_save_early_trials(p_rows jsonb) returns boolean
language plpgsql security invoker set search_path='' as $$
begin
 insert into public.dex_early_trials(id,first_at,address,payload)
 select (r->>'id')::uuid,to_timestamp((r->>'first_at')::double precision),r->>'address',r
 from jsonb_array_elements(p_rows) r where r->>'version'='early-v1'
 on conflict(id) do update set payload=excluded.payload;
 delete from public.dex_early_trials where first_at<now()-interval '7 days';
 return true;
end; $$;
revoke all on function public.dex_save_early_trials(jsonb) from public,anon,authenticated;
grant execute on function public.dex_save_early_trials(jsonb) to service_role;
