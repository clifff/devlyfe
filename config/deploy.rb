set :application, "devlyfe"
set :repository,  "git://github.com/clifff/devlyfe.git"

set :scm, :git
# Or: `accurev`, `bzr`, `cvs`, `darcs`, `git`, `mercurial`, `perforce`, `subversion` or `none`

role :web, "linode"                          # Your HTTP server, Apache/etc
set :user , "devlyfe"
set :deploy_to,  "/home/devlyfe"
set :use_sudo, false

set :deploy_via, :remote_cache

# if you want to clean up old releases on each deploy uncomment this:
after "deploy:restart", "deploy:cleanup"


task :bundle_install do
  run "cd #{release_path} && bundle install --deployment"
end
after "deploy:update_code", "bundle_install"
