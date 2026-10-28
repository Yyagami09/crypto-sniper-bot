-- Authentication, personal Telegram connections and durable delivery records.
create table public.sniper_profiles (
 id uuid primary key references auth.users(id) on delete cascade,
 username text not null unique check(username ~ '^[a-z0-9_]{3,32}$'),
 display_name text not null check(length(display_name) between 1 and 80),
 role text not null default 'user' check(role in ('admin','user')),
 active boolean not null default true,
 created_at timestamptz not null default now()
);
alter table public.sniper_profiles enable row level security;
revoke all on public.sniper_profiles from anon, authenticated;
grant select on public.sniper_profiles to authenticated;
grant all on public.sniper_profiles to service_role;
create policy own_profile on public.sniper_profiles for select to authenticated using(id=(select auth.uid()));
create policy service_profiles on public.sniper_profiles to service_role using(true) with check(true);

create function public.sniper_active() returns boolean language sql stable security invoker set search_path='' as $$
 select exists(select 1 from public.sniper_profiles where id=(select auth.uid()) and active);
$$;
create function public.sniper_admin() returns boolean language sql stable security invoker set search_path='' as $$
 select exists(select 1 from public.sniper_profiles where id=(select auth.uid()) and active and role='admin');
$$;
revoke all on function public.sniper_active(),public.sniper_admin() from public,anon;
grant execute on function public.sniper_active(),public.sniper_admin() to authenticated;

create table public.sniper_telegram (
 user_id uuid primary key references public.sniper_profiles(id) on delete cascade,
 bot_id bigint unique,
 bot_username text not null,
 secret_id uuid not null,
 challenge text not null,
 challenge_at timestamptz not null default now(),
 chat_id bigint,
 connected_at timestamptz,
 enabled boolean not null default false,
 last_test_at timestamptz
);
create table public.sniper_deliveries (
 user_id uuid not null references public.sniper_profiles(id) on delete cascade,
 alert_id text not null,
 status text not null default 'pending' check(status in ('pending','sent','failed')),
 attempts int not null default 0,
 next_attempt timestamptz not null default now(),
 created_at timestamptz not null default now(),
 sent_at timestamptz,
 primary key(user_id,alert_id)
);
create index sniper_delivery_created on public.sniper_deliveries(created_at);
alter table public.sniper_telegram enable row level security;
alter table public.sniper_deliveries enable row level security;
revoke all on public.sniper_telegram,public.sniper_deliveries from public,anon,authenticated;
grant all on public.sniper_telegram,public.sniper_deliveries to service_role;
create policy service_telegram on public.sniper_telegram to service_role using(true) with check(true);
create policy service_deliveries on public.sniper_deliveries to service_role using(true) with check(true);

-- Only trusted Edge Functions can invoke these Vault operations. User identity is
-- checked through Auth by the Edge Function, never taken from the request body.
create function public.sniper_save_telegram(p_user uuid,p_bot bigint,p_username text,p_token text,p_challenge text)
 returns void language plpgsql security definer set search_path='' as $$
declare sid uuid;
begin
 if coalesce(current_setting('request.jwt.claims',true)::jsonb->>'role','')<>'service_role' then raise exception 'service role required'; end if;
 select secret_id into sid from public.sniper_telegram where user_id=p_user for update;
 if exists(select 1 from public.sniper_telegram where bot_id=p_bot and user_id<>p_user) then raise exception 'bot already connected'; end if;
 if sid is null then sid:=vault.create_secret(p_token); else perform vault.update_secret(sid,p_token); end if;
 insert into public.sniper_telegram(user_id,bot_id,bot_username,secret_id,challenge)
 values(p_user,p_bot,p_username,sid,p_challenge)
 on conflict(user_id) do update set bot_id=excluded.bot_id,bot_username=excluded.bot_username,
 challenge=excluded.challenge,challenge_at=now(),chat_id=null,connected_at=null,enabled=false;
end; $$;

create function public.sniper_telegram_credentials(p_user uuid default null)
 returns jsonb language plpgsql security definer set search_path='' as $$
begin
 if coalesce(current_setting('request.jwt.claims',true)::jsonb->>'role','')<>'service_role' then raise exception 'service role required'; end if;
 return coalesce((select jsonb_agg(to_jsonb(t)||jsonb_build_object('token',v.decrypted_secret))
 from public.sniper_telegram t join public.sniper_profiles p on p.id=t.user_id and p.active
 join vault.decrypted_secrets v on v.id=t.secret_id
 where (p_user is null and t.enabled) or t.user_id=p_user),'[]'::jsonb);
end; $$;

create function public.sniper_disconnect_telegram(p_user uuid)
 returns void language plpgsql security definer set search_path='' as $$
declare sid uuid;
begin
 if coalesce(current_setting('request.jwt.claims',true)::jsonb->>'role','')<>'service_role' then raise exception 'service role required'; end if;
 select secret_id into sid from public.sniper_telegram where user_id=p_user for update;
 if sid is not null then
  perform vault.update_secret(sid,'');
  update public.sniper_telegram set bot_id=null,bot_username='',challenge='',chat_id=null,
   connected_at=null,enabled=false where user_id=p_user;
 end if;
end; $$;
revoke all on function public.sniper_save_telegram(uuid,bigint,text,text,text),public.sniper_telegram_credentials(uuid),public.sniper_disconnect_telegram(uuid) from public,anon,authenticated;
grant execute on function public.sniper_save_telegram(uuid,bigint,text,text,text),public.sniper_telegram_credentials(uuid),public.sniper_disconnect_telegram(uuid) to service_role;

-- The feed contains shared market data, but this application now requires login.
revoke select on public.pump_market_feed from anon;
alter policy market_feed_read on public.pump_market_feed to authenticated using(id='public' and public.sniper_active());

-- Existing Game Sniper portfolio remains an administrator workspace.
alter table public.crypto_games enable row level security;
revoke all on public.crypto_games from anon;
grant select,insert,update,delete on public.crypto_games to authenticated;
alter policy "Leitura publica permitida" on public.crypto_games to authenticated using(public.sniper_admin());
alter policy "Insercao permitida via API" on public.crypto_games to authenticated with check(public.sniper_admin());
alter policy "Deletar permitido via API" on public.crypto_games to authenticated using(public.sniper_admin());
alter policy "Permitir atualizacao publica" on public.crypto_games to authenticated using(public.sniper_admin()) with check(public.sniper_admin());
