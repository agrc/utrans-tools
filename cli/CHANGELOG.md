# Changelog

## [1.1.0](https://github.com/agrc/utrans-tools/compare/ugrc-utrans-tools-v1.0.1...ugrc-utrans-tools-v1.1.0) (2026-08-28)


### Features

* **cli:** add a script for discovering value_mapping values ([826d009](https://github.com/agrc/utrans-tools/commit/826d0096f0add9b4ed07c77f405d7624449bfb4e))
* **cli:** add timing metrics to etl command ([4dc99bc](https://github.com/agrc/utrans-tools/commit/4dc99bcdaf3c3cec7b266c0dcb4f4a688c55570a))
* **cli:** implement detect-changes command ([eed55c0](https://github.com/agrc/utrans-tools/commit/eed55c0f4c897fb3c6fd01c716451c0e6ac207c4))
* **cli:** implement value_mappings, rules, and custom_handler profile configs ([f8cca4a](https://github.com/agrc/utrans-tools/commit/f8cca4a54e6109ee1c0f45ce76a169b0f98185fd))


### Bug Fixes

* **cli:** apply reviewed mappings from Erik to profiles ([43de04e](https://github.com/agrc/utrans-tools/commit/43de04e3c8e651e5fc63fc964ccbb9e948ee0004))
* **cli:** don't add domains to etl output ([bd7b38d](https://github.com/agrc/utrans-tools/commit/bd7b38d9dc01d8a9d2fc70f53c2554a568db1a82))
* **cli:** don't try to insert invalid values that are longer than the fields length ([b373cdd](https://github.com/agrc/utrans-tools/commit/b373cdd65ad4caf8cadb3e8282fa44a5d67b8fba))
* **cli:** fix county name mapping to boundaries data for etl ([9a6f281](https://github.com/agrc/utrans-tools/commit/9a6f2816ef7370068094036dee33c6fe2b8bcc22))
* **cli:** fix fips values ([13619c0](https://github.com/agrc/utrans-tools/commit/13619c0220986a473d476ce9e219a035fa026406))
* **cli:** remove all superfluous and optional inputs ([2913f35](https://github.com/agrc/utrans-tools/commit/2913f3589d9dadaf41b7dae4fd8f552691c4a2c8))
* **cli:** remove superfluous require_fields profile config ([af7b2c8](https://github.com/agrc/utrans-tools/commit/af7b2c8fe26023dfb98fd432674bdb1acffdd7e2))
* **cli:** remove translate_vertical_levels in favor of value_mappings ([1c41974](https://github.com/agrc/utrans-tools/commit/1c41974076d840d16bbe5e8d60479004499b5982))

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
