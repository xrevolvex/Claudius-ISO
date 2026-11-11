// Claudius defaults for Firefox ESR. Users can change any of these in about:config.
// The number of content processes and the memory cache size are set per machine
// by claudius-tune (see claudius-adaptive.js).
pref("browser.startup.homepage", "file:///usr/share/claudius/start/index.html");
pref("browser.startup.page", 1);
pref("browser.newtabpage.enabled", false);
pref("browser.aboutwelcome.enabled", false);
pref("browser.shell.checkDefaultBrowser", false);
pref("browser.tabs.warnOnClose", false);
pref("browser.toolbars.bookmarks.visibility", "never");
pref("browser.sessionhistory.max_total_viewers", 2);
pref("browser.urlbar.suggest.quicksuggest.sponsored", false);
pref("browser.newtabpage.activity-stream.showSponsored", false);
pref("browser.newtabpage.activity-stream.showSponsoredTopSites", false);
pref("datareporting.healthreport.uploadEnabled", false);
pref("datareporting.policy.dataSubmissionEnabled", false);
pref("toolkit.telemetry.enabled", false);
pref("toolkit.telemetry.unified", false);
pref("app.shield.optoutstudies.enabled", false);
pref("extensions.pocket.enabled", false);
pref("gfx.webrender.software", true);
pref("layers.acceleration.disabled", false);
pref("media.hardware-video-decoding.enabled", false);
pref("ui.systemUsesDarkTheme", 1);
pref("layout.css.prefers-color-scheme.content-override", 0);
