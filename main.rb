require 'rubygems'
require 'nokogiri'
require 'open-uri'
require 'fileutils'
require 'erb'

def fetch_rss_feed(url)
  host = url.sub("http://", "")
  host = host.sub(/^www/, "")
  host = host.gsub(/\//, "_")

  tmp_dir = File.join( File.dirname(__FILE__), "tmp" )
  if !File.directory?( tmp_dir )
    FileUtils.mkdir( tmp_dir )
  end
  location = File.join(tmp_dir, "#{host}.xml")
  if File.exists?(location) && false
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

def hacker_news_processor(entry_xml)
  {
    :url => entry_xml.xpath("link").text,
    :comments => entry_xml.xpath("comments").text,
    :title => entry_xml.xpath("title").text,
  }
end

def vox_media_processor(entry_xml)
  data = {
    :url => entry_xml.xpath("link").attr("href").text,
    :title => entry_xml.xpath("title").text
  }
  data[:comments] = data[:url] + "#comments"
  data
end

def reddit_processor(entry_xml)
  data = {
    :comments => entry_xml.xpath("link").text,
    :title => entry_xml.xpath("title").text
  }
  doc = Nokogiri::HTML( entry_xml.xpath("description").text )
  data[:url] = doc.xpath('//a')[1].attr('href')
  data
end

@sites = [
  {
    :name => "Hacker News",
    :feed_url => "http://news.ycombinator.com/rss",
    :entry_xpath => "//item",
    :processor => :hacker_news_processor,
    :url => "http://news.ycombinator.com/"
  },
  {
    :name => "The Verge",
    :feed_url => "http://www.theverge.com/rss/index.xml",
    :entry_xpath => "//entry",
    :processor => :vox_media_processor,
    :url => "http://www.theverge.com"
  },
  {
    :name => "Polygon",
    :feed_url => "http://www.theverge.com/gaming/rss/index.xml",
    :entry_xpath => "//entry",
    :processor => :vox_media_processor,
    :url => "http://www.theverge.com/gaming"
  },
  {
    :name => "Proggit",
    :feed_url => "http://www.reddit.com/r/programming/.rss",
    :entry_xpath => "//item",
    :processor => :reddit_processor,
    :url => "http://www.reddit.com/r/programming/"
  }
]

@sites.each do |site|
  doc = Nokogiri::XML( fetch_rss_feed(site[:feed_url]) )
  doc.remove_namespaces!
  site[:entries] = []
  doc.xpath( site[:entry_xpath] ).each_with_index do |entry, i|
    next if i > 9
    site[:entries] << self.send(site[:processor], entry)
  end
end

base_dir = File.expand_path(File.dirname(__FILE__))
erb = ERB.new(
  File.open( File.join(base_dir, "index.html.erb") ).read
)
markup = erb.result(binding)
file = File.new( File.join(base_dir, "public", "index.html"), "w")
file.write(markup)
file.close
