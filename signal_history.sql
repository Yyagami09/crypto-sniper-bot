-- Durable, shared market-signal history; contains only the public-feed whitelist.
create table public.pump_signal_history (
 id uuid primary key,
 confirmed_at timestamptz not null,
 address text not null,
 payload jsonb not null,
 rules jsonb not null
);
create index pump_signal_history_recent on public.pump_signal_history(confirmed_at desc,id desc);
alter table public.pump_signal_history enable row level security;
revoke all on public.pump_signal_history from public,anon,authenticated;
grant select on public.pump_signal_history to authenticated;
grant select,insert,delete on public.pump_signal_history to service_role;
create policy active_signal_history on public.pump_signal_history for select to authenticated
 using((select public.sniper_active()) and confirmed_at>=now()-interval '24 hours' and confirmed_at<=now());
create policy signal_history_service on public.pump_signal_history to service_role using(true) with check(true);

-- Called by the existing collector. Feed and history commit atomically. Repeated
-- cycles cannot overwrite the original confirmation or extend its 24h window.
create or replace function public.pump_publish_market_feed(p_payload jsonb) returns boolean
language plpgsql security invoker set search_path='' as $$
begin
 if p_payload->>'profile' is distinct from 'free-market-v1' then raise exception 'invalid feed'; end if;
 insert into public.pump_signal_history(id,confirmed_at,address,payload,rules)
 select (a->>'id')::uuid,to_timestamp((a->>'created_at')::double precision),a->>'address',a,
        p_payload#>'{run,rules}'
 from jsonb_array_elements(coalesce(p_payload->'alerts','[]'::jsonb)) a
 where a->>'kind'='candidate' and a#>>'{snapshot,profile}'='free-market-v1'
   and (a->>'created_at')::double precision>=extract(epoch from now()-interval '24 hours')
   and (a->>'created_at')::double precision<=extract(epoch from now())
 on conflict(id) do nothing;
 delete from public.pump_signal_history where confirmed_at<now()-interval '24 hours';
 update public.pump_market_feed set payload=p_payload,updated_at=clock_timestamp() where id='public';
 return found;
end; $$;
revoke all on function public.pump_publish_market_feed(jsonb) from public,anon,authenticated;
grant execute on function public.pump_publish_market_feed(jsonb) to service_role;

-- Recover currently available confirmations without changing their timestamps.
insert into public.pump_signal_history(id,confirmed_at,address,payload,rules)
select (a->>'id')::uuid,to_timestamp((a->>'created_at')::double precision),a->>'address',a,payload#>'{run,rules}'
from public.pump_market_feed cross join lateral jsonb_array_elements(payload->'alerts') a
where id='public' and a->>'kind'='candidate' and a#>>'{snapshot,profile}'='free-market-v1'
 and (a->>'created_at')::double precision>=extract(epoch from now()-interval '24 hours')
 and (a->>'created_at')::double precision<=extract(epoch from now())
on conflict(id) do nothing;
