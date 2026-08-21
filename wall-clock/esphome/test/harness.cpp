// Stub harness mirroring the ESPHome lambda environment, so the render body can
// be type-checked without the full toolchain. Types copied from
// esphome/core/color.h and components/light/esp_color_view.h @ tag 2026.8.0.
#include <cstdint>
#include <cmath>
#include <string>
#include <algorithm>
#include <cstdio>

struct Color {
  uint8_t r{0}, g{0}, b{0}, w{0};
  constexpr Color() = default;
  constexpr Color(uint8_t red, uint8_t green, uint8_t blue) : r(red), g(green), b(blue), w(0) {}
  static const Color BLACK;
};
const Color Color::BLACK{0,0,0};

struct ESPColorView {
  Color *p;
  ESPColorView &operator=(const Color &rhs) { *p = rhs; return *this; }
  Color get() const { return *p; }
  uint8_t get_red() const { return p->r; }
};
struct ESPRangeView {
  Color *base; int n;
  ESPRangeView &operator=(const Color &rhs) { for (int i=0;i<n;i++) base[i]=rhs; return *this; }
};
struct AddressableLight {
  static const int MAX = 256;
  Color px[MAX]; int n;
  explicit AddressableLight(int count) : n(count) {}
  int32_t size() const { return n; }
  ESPColorView operator[](int32_t i) const {
    int32_t k = i < 0 ? i + n : i;
    return ESPColorView{const_cast<Color*>(&px[k])};
  }
  ESPRangeView all() { return ESPRangeView{px, n}; }
};

// --- ESPTime stand-in --------------------------------------------------------
struct ESPTime {
  uint8_t hour{0}, minute{0}, second{0};
  long timestamp{0};
  bool valid{true};
  bool is_valid() const { return valid; }
};

// --- id() targets ------------------------------------------------------------
struct NumT   { float state; };
struct SelT   { std::string state; };
struct SwT    { bool state; };
struct BinT   { bool state; };
struct SensT  { float state; };
struct TextT  { std::string state; };
struct TimeT  { ESPTime t; ESPTime now() const { return t; } };

static uint32_t g_frame = 0;
static bool     g_ha_connected = true;
static NumT  g_day{55}, g_night{8};
static SelT  g_mode{"auto"};
static SwT   g_display{true};
static BinT  g_alert{false}, g_bin{false}, g_garage{false}, g_unknown{false};
static BinT  g_sam{true}, g_laura{false}, g_amanda{true}, g_zac{false};
static SensT g_finish{NAN}, g_total{NAN};
static TextT g_nextbin{"Green waste"};
static TimeT g_time;

#define ID_frame              g_frame
#define ID_ha_connected       g_ha_connected
#define ID_day_brightness     g_day
#define ID_night_brightness   g_night
#define ID_display_mode       g_mode
#define ID_display_on         g_display
#define ID_timer_alert        g_alert
#define ID_bin_night          g_bin
#define ID_garage_open        g_garage
#define ID_driveway_unknown   g_unknown
#define ID_home_sam           g_sam
#define ID_home_laura         g_laura
#define ID_home_amanda        g_amanda
#define ID_home_zac           g_zac
#define ID_timer_finish_epoch g_finish
#define ID_timer_total_seconds g_total
#define ID_next_bin           g_nextbin
#define ID_ha_time            g_time
#define id(x) ID_##x

void render(AddressableLight &it, Color current_color, bool initial_run) {
#include "lambda_body.cpp"
}


static int brightest(AddressableLight &it, int n) {
  int best = -1; long bv = -1;
  for (int i = 0; i < n; i++) {
    long v = (long) it.px[i].r * 3 + it.px[i].g;   // weight red: hour hand is amber
    if (v > bv) { bv = v; best = i; }
  }
  return best;
}
static int fails = 0;
static void expect(const char *what, int got, int want) {
  bool ok = (got == want);
  if (!ok) fails++;
  printf("  [%s] %-42s got=%-4d want=%-4d\n", ok ? "PASS" : "FAIL", what, got, want);
}

int main() {
  struct Case { const char *name; void (*setup)(); };
  auto reset = []{
    g_frame = 0;
    g_mode.state="auto"; g_display.state=true; g_alert.state=false;
    g_bin.state=g_garage.state=g_unknown.state=false;
    g_finish.state=NAN; g_total.state=NAN;
    g_time.t = ESPTime{10, 8, 30, 1000000, true};
  };
  auto run = [&](const char *name, int leds) {
    AddressableLight it(leds);
    for (int f = 0; f < 90; f++) render(it, Color::BLACK, f == 0);
    int lit = 0; long sum = 0;
    for (int i = 0; i < leds; i++) {
      if (it.px[i].r || it.px[i].g || it.px[i].b) lit++;
      sum += it.px[i].r + it.px[i].g + it.px[i].b;
    }
    printf("  %-34s leds=%-3d lit=%-3d sum=%ld\n", name, leds, lit, sum);
  };

  printf("Render smoke tests (90 frames each):\n");
  for (int leds : {12, 16, 24, 60}) { reset(); run("clock, ring size sweep", leds); }
  reset(); g_time.t.valid = false;              run("no time yet -> crawl", 60);
  reset(); g_alert.state = true;                run("timer alert -> full ring", 60);
  reset(); g_finish.state = 1000060; g_total.state = 120;  run("timer arc, 50% drained", 60);
  reset(); g_finish.state = 1000060; g_total.state = 10;   run("timer arc, ratio>1 clamp", 60);
  reset(); g_bin.state = g_garage.state = g_unknown.state = true; run("ambient: all flags on", 60);
  reset(); g_nextbin.state = "Recycling"; g_bin.state = true;     run("ambient: recycling colour", 60);
  reset(); g_display.state = false;             run("display off -> blank", 60);
  reset(); g_mode.state = "test chase";         run("test chase", 60);
  reset(); g_mode.state = "clock bare";         run("clock bare", 60);
  reset(); g_ha_connected = false;              run("HA down -> stale hint", 60);
  g_ha_connected = true;
  reset(); g_time.t = ESPTime{23, 30, 0, 1000000, true};  run("night window -> dimmed", 60);
  reset(); g_time.t = ESPTime{0, 0, 0, 1000000, true};    run("midnight wrap -> dimmed", 60);

  printf("\nHand-position assertions (hour hand = brightest amber pixel):\n");
  struct { int h, m, leds, want; const char *label; } cases[] = {
    {12, 0, 60,  0, "12:00 on 60 -> pixel 0"},
    { 3, 0, 60, 15, "03:00 on 60 -> pixel 15"},
    { 6, 0, 60, 30, "06:00 on 60 -> pixel 30"},
    { 9, 0, 60, 45, "09:00 on 60 -> pixel 45"},
    { 3, 0, 24,  6, "03:00 on 24 -> pixel 6"},
    { 6, 0, 24, 12, "06:00 on 24 -> pixel 12"},
    { 3, 0, 12,  3, "03:00 on 12 -> pixel 3"},
  };
  for (auto &c : cases) {
    reset(); g_time.t = ESPTime{(uint8_t)c.h, (uint8_t)c.m, 0, 1000000, true};
    g_mode.state = "clock bare"; g_day.state = 100;
    AddressableLight it(c.leds);
    render(it, Color::BLACK, true);
    expect("hour", brightest(it, c.leds), c.want);
  }

  printf("\nFull-ring coverage (alert must light every pixel at any size):\n");
  for (int leds : {12, 24, 60}) {
    reset(); g_alert.state = true; g_day.state = 100;
    AddressableLight it(leds);
    render(it, Color::BLACK, true);
    int lit = 0;
    for (int i = 0; i < leds; i++) if (it.px[i].r) lit++;
    expect("alert lights all", lit, leds);
  }

  printf("\n%s (%d failures)\n", fails ? "FAILURES PRESENT" : "All assertions passed", fails);
  return fails ? 1 : 0;
}
