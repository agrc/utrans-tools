# Changelog

## [1.0.1](https://github.com/agrc/utrans-tools/compare/ugrc-utrans-tools-v1.0.0...ugrc-utrans-tools-v1.0.1) (2026-08-20)


### Bug Fixes

* **cli:** make sure that UTRANS_NOTES values are truncated to 200 characters during etl ([1676c43](https://github.com/agrc/utrans-tools/commit/1676c431efd3a492cc43d5f3e014a378ca649413))
* **cli:** preserve invalid values for coded-value domain fields ([ef3897a](https://github.com/agrc/utrans-tools/commit/ef3897a17f080450f52f76cbcfa5d69d7bd21009)), closes [#19](https://github.com/agrc/utrans-tools/issues/19)

## [1.0.0](https://github.com/agrc/utrans-tools/compare/ugrc-utrans-tools-v0.1.0...ugrc-utrans-tools-v1.0.0) (2026-08-19)


### chore

* release 1.0.0 ([d56bcef](https://github.com/agrc/utrans-tools/commit/d56bcef05e1a6d50f3725bbac2f3691532f34dad))


### Features

* **cli:** add version banner and action ([ff6b6a4](https://github.com/agrc/utrans-tools/commit/ff6b6a47c45b3311d02fd7da17ab3ffa9ee80892))
* **cli:** convert to python cli ready for pypi publishing ([4f7e020](https://github.com/agrc/utrans-tools/commit/4f7e020b379d2489226202e3e74b8a4a9833304f))
* **cli:** implement etl command ([29cf37c](https://github.com/agrc/utrans-tools/commit/29cf37ce49bec4666ad05af5186c8622b5ac0152))
* county script migration ([e8c691c](https://github.com/agrc/utrans-tools/commit/e8c691cff9300c67f42d14160b4c1c3ea503db48))


### Bug Fixes

* address review comments - SystemExit handling, URL fix, and Python capitalization ([cbdfa27](https://github.com/agrc/utrans-tools/commit/cbdfa272b9503e73dbb46d6999c3834e85009121))
* compare fields used to avoid converting nulls to 0 for things like RoadName, where we actually want null ([deec8f5](https://github.com/agrc/utrans-tools/commit/deec8f51113d850e29424b31a9c8a84c76afa650))
* normalize all ([5870192](https://github.com/agrc/utrans-tools/commit/58701929b882e258da707ac3b6ec5db7b2c9b9be))


### Documentation

* update README.md ([ab23a3d](https://github.com/agrc/utrans-tools/commit/ab23a3dd14206fea7765ce508e5cb49699c2861f))
