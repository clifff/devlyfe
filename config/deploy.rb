require "bundler/capistrano"

set :application, "devlyfe"
set :repository,  "git://github.com/clifff/devlyfe.git"

set :scm, :git

role :web, "linode"
set :user , "devlyfe"
set :deploy_to,  "/home/devlyfe"
set :use_sudo, false

set :deploy_via, :remote_cache

# if you want to clean up old releases on each deploy uncomment this:
after "deploy:restart", "deploy:cleanup"

before "deploy:create_symlink" do 
  run "cd #{release_path} && bundle exec ruby main.rb"
end
