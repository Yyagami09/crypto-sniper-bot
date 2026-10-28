alter table public.sniper_profiles add column if not exists manual_requested_at timestamptz;
create or replace function public.sniper_reserve_manual(p_user uuid) returns boolean
language plpgsql security invoker set search_path='' as $$
begin
 update public.sniper_profiles set manual_requested_at=clock_timestamp()
 where id=p_user and active and (manual_requested_at is null or manual_requested_at<clock_timestamp()-interval '30 seconds');
 return found;
end; $$;
revoke all on function public.sniper_reserve_manual(uuid) from public,anon,authenticated;
grant execute on function public.sniper_reserve_manual(uuid) to service_role;
