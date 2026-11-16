from resources.lib.trailer_service import TrailerAutoplay


class FakeKodi:
    def __init__(self):
        self.labels = {'ListItem.DBType': 'movie', 'ListItem.UniqueID(tmdb)': '603',
                       'ListItem.IMDBNumber': 'tt0133093', 'ListItem.Title': 'Matrix', 'ListItem.Year': '1999'}
        self.conds = {'Window.IsActive(home)': True}
        self.now = 0.0

    def info(self, label):
        return self.labels.get(label, '')

    def cond(self, expr):
        return self.conds.get(expr, False)

    def clock(self):
        return self.now


class FakePlayer:
    def __init__(self):
        self.played, self.stopped, self.starts, self.playing = [], 0, 0, False

    def play(self, url):
        self.played.append(url)
        self.starts += 1
        self.playing = True

    def stop(self):
        self.stopped += 1
        self.playing = False

    def is_playing(self):
        return self.playing

    def started_count(self):
        return self.starts


def make(enabled=True, key='es1', on_resolve=None):
    k, p = FakeKodi(), FakePlayer()
    calls = []

    def resolve(kind, tmdb, imdb, title, year):
        calls.append((kind, tmdb, imdb, title, year))
        if on_resolve:
            on_resolve(k)
        return key

    s = TrailerAutoplay(k.info, k.cond, p, resolve, lambda: enabled, k.clock)
    return s, k, p, calls


def run(s, k, seconds, step=0.5):
    end = k.now + seconds
    while k.now < end:
        s.tick()
        k.now += step
    s.tick()


def test_plays_spanish_trailer_after_four_seconds_not_before():
    s, k, p, calls = make()
    run(s, k, 3.5)
    assert p.played == []
    run(s, k, 1.0)
    assert p.played == ['plugin://plugin.video.youtube/play/?video_id=es1']
    assert calls == [('movie', '603', 'tt0133093', 'Matrix', '1999')]
    run(s, k, 10)
    assert len(p.played) == 1  # once per focus


def test_tvshow_uses_tv_kind_and_other_types_are_ignored():
    s, k, p, calls = make()
    k.labels['ListItem.DBType'] = 'tvshow'
    run(s, k, 5)
    assert calls[0][0] == 'tv'
    s, k, p, calls = make()
    k.labels['ListItem.DBType'] = ''  # sports channel / folder
    run(s, k, 10)
    assert p.played == [] and calls == []


def test_focus_change_stops_our_trailer():
    s, k, p, _ = make()
    run(s, k, 5)
    k.labels['ListItem.Title'] = 'Otra'
    k.labels['ListItem.UniqueID(tmdb)'] = '604'
    s.tick()
    assert p.stopped == 1


def test_never_stops_dads_movie():
    s, k, p, _ = make()
    run(s, k, 5)
    p.play('plugin://plugin.video.palantir3/?play=movie')  # dad pressed play
    k.labels['ListItem.Title'] = 'Otra'
    s.tick()
    assert p.stopped == 0


def test_never_stops_while_fullscreen():
    s, k, p, _ = make()
    run(s, k, 5)
    k.conds['Window.IsActive(fullscreenvideo)'] = True
    k.conds['Window.IsActive(home)'] = False
    s.tick()
    assert p.stopped == 0


def test_does_not_start_when_something_else_plays():
    s, k, p, calls = make()
    p.playing = True
    run(s, k, 10)
    assert p.played == [] and calls == []


def test_disabled_or_outside_menus_does_nothing():
    s, k, p, calls = make(enabled=False)
    run(s, k, 10)
    assert p.played == []
    s, k, p, calls = make()
    k.conds['Window.IsActive(home)'] = False
    run(s, k, 10)
    assert p.played == [] and calls == []


def test_no_spain_trailer_plays_nothing():
    s, k, p, calls = make(key=None)
    run(s, k, 10)
    assert p.played == [] and len(calls) == 1


def test_focus_moved_while_resolving_plays_nothing():
    def move(k):
        k.labels['ListItem.Title'] = 'Otra'
    s, k, p, _ = make(on_resolve=move)
    run(s, k, 5)
    assert p.played == []
