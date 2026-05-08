create table if not exists public.site_content (
  id bigint primary key,
  data jsonb not null
);

create table if not exists public.admin_user (
  id bigint primary key,
  username text not null,
  password_hash text not null
);

insert into public.site_content (id, data)
values (1, '{}'::jsonb)
on conflict (id) do nothing;

insert into public.admin_user (id, username, password_hash)
values (1, 'admin', '')
on conflict (id) do nothing;
