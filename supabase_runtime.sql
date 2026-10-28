create extension if not exists pg_cron;
create extension if not exists pg_net with schema extensions;

do $$ begin
 if not exists(select 1 from vault.secrets where name='pump_cron_token') then
  perform vault.create_secret(gen_random_uuid()::text||gen_random_uuid()::text,'pump_cron_token','Autenticação interna do radar');
 end if;
end $$;

-- Narrow privileged lookup: only the service role may call; no anon access.
create or replace function public.pump_worker_config() returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 if coalesce(current_setting('request.jwt.claims',true)::jsonb->>'role','')<>'service_role' then
  raise exception 'service role required';
 end if;
 return (select jsonb_build_object(
  'cron_token',max(decrypted_secret) filter(where name='pump_cron_token'),
  'gmgn_key',max(decrypted_secret) filter(where name='gmgn_api_key'),
  'telegram_token',max(decrypted_secret) filter(where name='pump_telegram_bot_token'),
  'telegram_chat',max(decrypted_secret) filter(where name='pump_telegram_chat_id'))
  from vault.decrypted_secrets where name in ('pump_cron_token','gmgn_api_key','pump_telegram_bot_token','pump_telegram_chat_id'));
end; $$;
revoke all on function public.pump_worker_config() from public,anon,authenticated;
grant execute on function public.pump_worker_config() to service_role;

create or replace function public.pump_tick() returns bigint
language plpgsql security invoker set search_path='' as $$
declare token text; request_id bigint;
begin
 -- No requests to GMGN/Edge until the user supplies their own API key.
 if not exists(select 1 from vault.secrets where name='gmgn_api_key') then return null; end if;
 select decrypted_secret into token from vault.decrypted_secrets where name='pump_cron_token';
 select net.http_post(
  url:='https://qcetrltyhmtrgtijuiri.supabase.co/functions/v1/pump-radar',
  headers:=jsonb_build_object('Content-Type','application/json','x-pump-token',token),
  body:='{}'::jsonb,timeout_milliseconds:=115000) into request_id;
 return request_id;
end; $$;
revoke all on function public.pump_tick() from public,anon,authenticated,service_role;

update public.pump_radar_state set payload=jsonb_set(payload,'{run}',
 '{"status":"missing_key","engine":"supabase-edge","demo":false}'::jsonb)
 where id='main' and payload->'run'='{}'::jsonb;

select cron.schedule('pump-radar-every-minute','* * * * *','select public.pump_tick();')
where not exists(select 1 from cron.job where jobname='pump-radar-every-minute');

create policy pump_service_role on public.pump_radar_state for all to service_role using (true) with check (true);
