
## Harvest v5-v7 (22 Nov, post-cleanup)
- Added working sources: elmahal (scrap/copper pages), masrtimes, alnaharegypt, elfahd (sand/gravel), bscogroup, aac-siporex, kaydc-eg, tibawood, futureforimport, beshaysteel, builderspipes, almasryalyoum, scrapacbuyer, cairosteelcs, alnafie-steel, alinmasteel, alhusseinsteel, woodshop.com.eg, egyptplywood, aleqaria, elwatannews, pricedalil.
- Dead: egyptian-copper.com DNS, egyin/vetogate/algomhor 403, elkayansteel/eltawheed-metal/gtco-egypt 404, khurda.net needs JS browser.
- News sidebars = heavy junk (gold/money/people/logos). Every class grid eyeballed; verdicts applied.
- FINAL REVIEWED COUNTS (269 clean): copper_red 3, steel_scrap 3, brass 4, aluminum_shavings 5, copper_scrap 5, brick_white 6, steel_pipes 6, aluminum_soft 7, sand 7, gravel 9, plastic_jerrican 9, plastic_shredded 9, steel_rebar 9, steel_sheet 9, mdf 10, plastic_pet 10, steel_sections 10, cement_bags 12, wood_swed 16, plywood 17, wood_zan 17, brick_red 19, aluminum_profile 22.
- NEXT: build_dataset.py (85/15, dataset2.yaml, 23 classes) -> train yolov8n imgsz320 30ep chunks (vision/resume.py) -> validate -> honest metrics -> docs + integration mat_map update.
