require 'rubygems'
require 'nokogiri'
require 'open-uri'
require 'fileutils'
require 'erb'

def fetch_rss_feed(url)
  host = url.sub("http://", "")
  host = host.sub(/^www/, "")
  host = host.gsub(/\//, "_")

  tmp_dir = File.join( File.dirname(__FILE__) )
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

@sites = [
  {
    :name => "Hacker News",
    :feed_url => "http://news.ycombinator.com/rss",
    :entry_xpath => "//item",
    :url => "http://news.ycombinator.com/"
  },
  {
    :name => "The Verge",
    :feed_url => "http://www.theverge.com/rss/index.xml",
    :entry_xpath => "//entry",
    :url => "http://www.theverge.com"
  },
  {
    :name => "Polygon",
    :feed_url => "http://www.theverge.com/gaming/rss/index.xml",
    :entry_xpath => "//entry",
    :url => "http://www.theverge.com/gaming"
  }
]

@sites.each do |site|
  doc = Nokogiri::XML( fetch_rss_feed(site[:feed_url]) )
  doc.remove_namespaces!
  site[:entries] = []
  doc.xpath( site[:entry_xpath] ).each_with_index do |entry, i|
    next if i > 9

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

erb = ERB.new( File.open("index.html.erb").read )
markup = erb.result(binding)
file = File.new("index.html", "w")
file.write(markup)
file.close
