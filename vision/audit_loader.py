#!/usr/bin/env python3
"""Audit the actual Ultralytics loader, without loading weights or computing model metrics."""
import collections
import json
import shutil
import tempfile
from pathlib import Path
import ultralytics
from ultralytics.data.dataset import YOLODataset
from integrity_guard import ROOT, verify_snapshot

def main():
    manifest = verify_snapshot()
    names = {i:c for i,c in enumerate(manifest['classes'])}
    report = dict(ultralytics_version=ultralytics.__version__, model_loaded=False,
        metrics_computed=False, snapshot_hashes_verified=True, splits={})
    with tempfile.TemporaryDirectory(prefix='barter-loader-audit-') as tmp:
        for split in ('train', 'val'):
            src = ROOT / ('evaluation/legacy62_v1' if split=='val' else 'data/yolo3')
            dest = Path(tmp) / split
            for category in ('images', 'labels'):
                source = src/category if split=='val' else src/category/'train'
                shutil.copytree(source, dest/category)
            ds = YOLODataset(img_path=str(dest/'images'), data={'names':names,'nc':len(names)},
                imgsz=320, augment=False, cache=False, batch_size=8, prefix=split+': ')
            loaded = [Path(p).name for p in ds.im_files]
            expected = sorted(p.name for p in (dest/'images').glob('*.jpg'))
            assert sorted(loaded)==expected
            assert len(set(loaded))==len(loaded)
            seen = collections.Counter()
            for i in range(len(ds)):
                item = ds[i]
                seen[Path(item['im_file']).name] += 1
                assert item['cls'].numel()==1
                expected_id = manifest['classes'].index(Path(item['im_file']).name.split('__')[0])
                assert int(item['cls'].item()) == expected_id
            assert set(seen.values())=={1}
            report['splits'][split] = dict(loader_examples=len(ds), unique_filenames=len(set(loaded)),
                each_example_yielded_once=True, labels_match_class_prefix=True,
                caveat='Unique filenames do not prove independent images, labels or suppliers.')
    verify_snapshot()
    (ROOT/'evaluation/loader_audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__=='__main__':
    main()
