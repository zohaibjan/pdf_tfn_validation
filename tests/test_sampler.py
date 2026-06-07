from pathlib import Path

from file_flag import sampler


def _make_repo(tmp_path: Path) -> Path:
    # folder A: 10 files, folder B: 20 files, folder C: 4 files
    layout = {"A": 10, "B/sub": 20, "C": 4}
    for rel, n in layout.items():
        d = tmp_path / rel
        d.mkdir(parents=True)
        for i in range(n):
            (d / f"f{i}.pdf").write_text("x")
    # a non-pdf that must be ignored
    (tmp_path / "A" / "note.txt").write_text("ignore me")
    return tmp_path


def test_discover_groups_by_folder(tmp_path):
    repo = _make_repo(tmp_path)
    by_folder = sampler.discover(repo)
    assert len(by_folder) == 3
    assert sum(len(v) for v in by_folder.values()) == 34


def test_proportional_samples_per_folder(tmp_path):
    repo = _make_repo(tmp_path)
    by_folder = sampler.discover(repo)
    picked = sampler.sample(by_folder, percent=50, strategy="proportional", seed=1)
    # 50% of 10, 20, 4 -> 5 + 10 + 2 = 17
    assert len(picked) == 17


def test_min_per_folder_enforced(tmp_path):
    repo = _make_repo(tmp_path)
    by_folder = sampler.discover(repo)
    # tiny percent still yields at least 1 per folder
    picked = sampler.sample(by_folder, percent=1, strategy="proportional",
                            seed=1, min_per_folder=1)
    assert len(picked) == 3


def test_equal_strategy_balances_folders(tmp_path):
    repo = _make_repo(tmp_path)
    by_folder = sampler.discover(repo)
    picked = sampler.sample(by_folder, percent=30, strategy="equal", seed=1)
    # budget = ceil(34*0.3)=11, per_folder=ceil(11/3)=4 -> 4+4+4 capped by size
    # C only has 4, so 4+4+4 = 12
    counts = {}
    for p in picked:
        counts[p.parent] = counts.get(p.parent, 0) + 1
    assert all(c <= 4 for c in counts.values())
    assert max(counts.values()) - min(counts.values()) <= 1 or min(counts.values()) == 4


def test_seed_is_reproducible(tmp_path):
    repo = _make_repo(tmp_path)
    by_folder = sampler.discover(repo)
    a = sampler.sample(by_folder, percent=40, seed=99)
    b = sampler.sample(by_folder, percent=40, seed=99)
    assert a == b
