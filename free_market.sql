-- Public, shared market feed only. Private state/Vault/portfolio remain inaccessible.
create table if not exists public.pump_market_feed (
 id text primary key check(id='public'),
 payload jsonb not null default '{"profile":"free-market-v1","tokens":{},"alerts":[],"run":{},"backoff_until":0}'::jsonb,
 updated_at timestamptz not null default now()
);
insert into public.pump_market_feed(id) values('public') on conflict do nothing;
alter table public.pump_market_feed enable row level security;
revoke all on public.pump_market_feed from anon,authenticated;
grant select on public.pump_market_feed to anon,authenticated;
grant select,update on public.pump_market_feed to service_role;
create policy market_feed_read on public.pump_market_feed for select to anon,authenticated using(id='public');
create policy market_feed_service on public.pump_market_feed for all to service_role using(true) with check(true);
create or replace function public.pump_publish_market_feed(p_payload jsonb) returns boolean
language plpgsql security invoker set search_path='' as $$
begin
 if p_payload->>'profile'<>'free-market-v1' then raise exception 'invalid feed'; end if;
 update public.pump_market_feed set payload=p_payload,updated_at=clock_timestamp() where id='public';
 return found;
end; $$;
revoke all on function public.pump_publish_market_feed(jsonb) from public,anon,authenticated;
grant execute on function public.pump_publish_market_feed(jsonb) to service_role;

create or replace function public.pump_tick() returns bigint
language plpgsql security invoker set search_path='' as $$
declare token text; request_id bigint;
begin
 select decrypted_secret into token from vault.decrypted_secrets where name='pump_cron_token';
 select net.http_post(
  url:='https://qcetrltyhmtrgtijuiri.supabase.co/functions/v1/pump-radar',
  headers:=jsonb_build_object('Content-Type','application/json','x-pump-token',token),
  body:='{}'::jsonb,timeout_milliseconds:=115000) into request_id;
 return request_id;
end; $$;
revoke all on function public.pump_tick() from public,anon,authenticated,service_role;
select cron.schedule('pump-radar-every-minute','* * * * *','select public.pump_tick();');
