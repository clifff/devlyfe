require 'rubygems'
require 'nokogiri'
require 'open-uri'
require 'fileutils'
require 'erb'

def render_to_file
  erb = ERB.new( File.open("index.html.erb").read )
  markup = erb.result(binding)
  file = File.new("index.html", "w")
  file.write(markup)
  file.close
end

def fetch_rss_feed(url)
  host = URI.parse(url).host
  if !File.directory?("tmp")
    FileUtils.mkdir("tmp")
  end
  location = "tmp/#{host}.xml"
  if File.exists?(location)
    puts "READING FROM FILE"
    feed = File.open(location).read
  else
    puts "STEALING FROM INTERNET"
    feed = open(url).read
    f = File.new(location, "w")
    f.write(feed)
    f.close
  end
  feed
end

@sites = [
  {
    :name => "The Verge",
    :feed_url => "http://www.theverge.com/rss/index.xml",
    :entry_xpath => "//entry",
    :url => "http://www.theverge.com"
  },
  {
    :name => "Hacker News",
    :feed_url => "http://news.ycombinator.com/rss",
    :entry_xpath => "//item",
    :url => "http://news.ycombinator.com/"
  }
]

@sites.each do |site|
  doc = Nokogiri::XML( fetch_rss_feed(site[:feed_url]) )
  doc.remove_namespaces!
  site[:entries] = []
  doc.xpath( site[:entry_xpath] ).each do |entry|

    # TODO: Ugh, need a better way of differentating between feeds. Hopefully just an RSS/Atom thing?
    link = entry.xpath("link")
    url = if link.attr('href')
      link.attr('href').text
    else
      link.text
    end

    site[:entries] << {
      :title => entry.xpath("title").text,
      :url => url
    }
  end
end

render_to_file