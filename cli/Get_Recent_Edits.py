"""Unified recent-edits runner for county road change detection.

Requires explicit full feature class paths:
- `--update-features`
- `--base-features`

County wrappers can dispatch here with a fixed `--county` value.
"""

import argparse
import os
import time
from dataclasses import dataclass, field

import arcpy


@dataclass
class DavisSchema:
    description: str
    text_fields: list[str]
    numeric_fields: list[str]
    compare_pairs: list[tuple[str, str]]


@dataclass
class CountyProfile:
    key: str
    aliases: list[str]
    display_name: str
    default_match_fields: str
    default_compare_fields: str | None
    text_fields: list[str] = field(default_factory=list)
    numeric_fields: list[str] = field(default_factory=list)
    uppercase_normalize_fields: set[str] = field(default_factory=set)
    normalize_mode: str = "strip_blank"
    default_dfc_output_name: str = "DFC_CountyToCounty"
    default_stats_table_name: str = "stats_county_to_county"
    default_recents_name: str = "RoadCenterline_Recents"
    davis_schemas: dict[str, DavisSchema] | None = None


PROFILES = {
    "beaver": CountyProfile(
        key="beaver",
        aliases=["beaver"],
        display_name="Beaver",
        default_match_fields="STREETNAME STREETNAME",
        default_compare_fields=(
            "PREDIR PREDIR; STREETNAME STREETNAME; STREETTYPE STREETTYPE; "
            "L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD; "
            "ALIAS1 ALIAS1; ALIAS1TYP ALIAS1TYP; ACSNAME ACSNAME; ACSSUF ACSSUF; "
            "SUFDIR SUFDIR"
        ),
        text_fields=["PREDIR", "STREETNAME", "STREETTYPE", "SUFDIR", "ALIAS1", "ALIAS1TYP", "ACSNAME", "ACSSUF"],
        numeric_fields=["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_BeaverToBeaver",
        default_stats_table_name="stats_beaver_to_beaver",
    ),
    "boxelder": CountyProfile(
        key="boxelder",
        aliases=["boxelder", "box elder"],
        display_name="Box Elder",
        default_match_fields="S_NAME S_NAME",
        default_compare_fields=(
            "L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD; "
            "PRE_DIR PRE_DIR; S_NAME S_NAME; S_TYPE S_TYPE; SUF_DIR SUF_DIR; "
            "ACS_ALIAS ACS_ALIAS; ACS_NAME ACS_NAME; ACS_SUF ACS_SUF; "
            "ALIAS1 ALIAS1; ALIAS1_TYP ALIAS1_TYP; ALIAS2 ALIAS2; "
            "ALIAS2_TYP ALIAS2_TYP"
        ),
        text_fields=["PRE_DIR", "S_NAME", "S_TYPE", "SUF_DIR", "ACS_ALIAS", "ACS_NAME", "ACS_SUF", "ALIAS1", "ALIAS1_TYP", "ALIAS2", "ALIAS2_TYP"],
        numeric_fields=["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_BoxElderToBoxElder",
        default_stats_table_name="stats_boxelder_to_boxelder",
    ),
    "cache": CountyProfile(
        key="cache",
        aliases=["cache"],
        display_name="Cache",
        default_match_fields="GEOCODEST GEOCODEST",
        default_compare_fields=(
            "PRE_DIR PRE_DIR; GEOCODEST GEOCODEST; TYPE TYPE; FAL FAL; TAL TAL; "
            "FAR FAR; TAR TAR; AliasPreDir AliasPreDir; AliasStreet AliasStreet; "
            "AliasType AliasType; AliasSufDir AliasSufDir; SUFFDIR SUFFDIR"
        ),
        text_fields=["PRE_DIR", "GEOCODEST", "TYPE", "SUFFDIR", "AliasPreDir", "AliasStreet", "AliasType", "AliasSufDir"],
        numeric_fields=["FAL", "TAL", "FAR", "TAR"],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_CacheToCache",
        default_stats_table_name="stats_cache_to_cache",
    ),
    "daggett": CountyProfile(
        key="daggett",
        aliases=["daggett"],
        display_name="Daggett",
        default_match_fields="S_NAME S_NAME",
        default_compare_fields=(
            "PRE_DIR PRE_DIR; S_NAME S_NAME; S_TYPE S_TYPE; L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; "
            "R_F_ADD R_F_ADD; R_T_ADD R_T_ADD; ACS_ALIAS ACS_ALIAS; SUF_DIR SUF_DIR"
        ),
        text_fields=["PRE_DIR", "S_NAME", "S_TYPE", "SUF_DIR", "ACS_ALIAS"],
        numeric_fields=["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_DaggettToDaggett",
        default_stats_table_name="stats_daggett_to_daggett",
    ),
    "duchesne": CountyProfile(
        key="duchesne",
        aliases=["duchesne"],
        display_name="Duchesne",
        default_match_fields="STREETNAME STREETNAME",
        default_compare_fields=(
            "PREDIR PREDIR; STREETNAME STREETNAME; STREETTYPE STREETTYPE; L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; "
            "R_F_ADD R_F_ADD; R_T_ADD R_T_ADD; ALIAS1 ALIAS1; ALIAS1TYPE ALIAS1TYPE; ALIAS2 ALIAS2; "
            "ALIAS2TYPE ALIAS2TYPE; ACSNAME ACSNAME; ACSSUF ACSSUF; SUFDIR SUFDIR"
        ),
        text_fields=["PREDIR", "STREETNAME", "STREETTYPE", "SUFDIR", "ALIAS1", "ALIAS1TYPE", "ALIAS2", "ALIAS2TYPE", "ACSNAME", "ACSSUF"],
        numeric_fields=["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_DuchesneToDuchesne",
        default_stats_table_name="stats_duchesne_to_duchesne",
    ),
    "emery": CountyProfile(
        key="emery",
        aliases=["emery"],
        display_name="Emery",
        default_match_fields="S_NAME S_NAME",
        default_compare_fields=(
            "PRE_DIR PRE_DIR; S_NAME S_NAME; S_TYPE S_TYPE; L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; "
            "R_F_ADD R_F_ADD; R_T_ADD R_T_ADD; ALIAS1 ALIAS1; ALIAS1_TYP ALIAS1_TYP; ALIAS2 ALIAS2; "
            "ALIAS2_TYP ALIAS2_TYP; SUF_DIR SUF_DIR"
        ),
        text_fields=["PRE_DIR", "S_NAME", "S_TYPE", "SUF_DIR", "ALIAS1", "ALIAS1_TYP", "ALIAS2", "ALIAS2_TYP"],
        numeric_fields=["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_EmeryToEmery",
        default_stats_table_name="stats_emery_to_emery",
    ),
    "carbon": CountyProfile(
        key="carbon",
        aliases=["carbon"],
        display_name="Carbon",
        default_match_fields="NAME NAME",
        default_compare_fields=(
            "PREDIR PREDIR; NAME NAME; POSTTYPE POSTTYPE; POSTDIR POSTDIR; "
            "FROMADDR_L FROMADDR_L; TOADDR_L TOADDR_L; "
            "FROMADDR_R FROMADDR_R; TOADDR_R TOADDR_R"
        ),
        text_fields=["PREDIR", "NAME", "POSTTYPE", "POSTDIR", "AN_NAME"],
        numeric_fields=["FROMADDR_L", "TOADDR_L", "FROMADDR_R", "TOADDR_R"],
        normalize_mode="strip_blank",
        default_dfc_output_name="DFC_CarbonToCarbon",
        default_stats_table_name="new_roads_stats_carbon",
    ),
    "garfield": CountyProfile(
        key="garfield",
        aliases=["garfield"],
        display_name="Garfield",
        default_match_fields="NAME NAME",
        default_compare_fields=(
            "FROMADDR_L FROMADDR_L; TOADDR_L TOADDR_L; FROMADDR_R FROMADDR_R; "
            "TOADDR_R TOADDR_R; NAME NAME; PREDIR PREDIR; POSTDIR POSTDIR; "
            "POSTTYPE POSTTYPE; AN_NAME AN_NAME; A1_NAME A1_NAME; A2_NAME A2_NAME"
        ),
        text_fields=["NAME", "PREDIR", "POSTDIR", "POSTTYPE", "AN_NAME", "A1_NAME", "A2_NAME"],
        numeric_fields=["FROMADDR_L", "TOADDR_L", "FROMADDR_R", "TOADDR_R"],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_GarfieldToGarfield",
        default_stats_table_name="stats_Garfield_to_Garfield",
    ),
    "grand": CountyProfile(
        key="grand",
        aliases=["grand"],
        display_name="Grand",
        default_match_fields="STREETNAME STREETNAME",
        default_compare_fields=(
            "L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD; "
            "STREETNAME STREETNAME; PREDIR PREDIR; SUFDIR SUFDIR; "
            "STREETTYPE STREETTYPE; ACSALIAS ACSALIAS; ALIAS1 ALIAS1; ALIAS2 ALIAS2"
        ),
        text_fields=["STREETNAME", "PREDIR", "STREETTYPE", "ACSALIAS", "ALIAS1", "ALIAS2"],
        numeric_fields=["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"],
        uppercase_normalize_fields={"STREETNAME", "STREETTYPE", "ACSALIAS", "ALIAS1", "ALIAS2"},
        normalize_mode="grand_legacy",
        default_dfc_output_name="DFC_GrandtoGrand",
        default_stats_table_name="stats_grand_to_grand",
    ),
    "iron": CountyProfile(
        key="iron",
        aliases=["iron"],
        display_name="Iron",
        default_match_fields="STREETNAME STREETNAME",
        default_compare_fields=(
            "PREDIR PREDIR; STREETNAME STREETNAME; STREETTYPE STREETTYPE; SUFDIR SUFDIR; "
            "ALIAS1 ALIAS1; ALIAS1TYPE ALIAS1TYPE; ALIAS2 ALIAS2; ALIAS2TYPE ALIAS2TYPE; "
            "ACSALIAS ACSALIAS; ACSNAME ACSNAME; ACSSUF ACSSUF; "
            "L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD"
        ),
        text_fields=["PREDIR", "STREETNAME", "STREETTYPE", "SUFDIR", "ALIAS1", "ALIAS1TYPE", "ALIAS2", "ALIAS2TYPE", "ACSALIAS", "ACSNAME", "ACSSUF"],
        numeric_fields=["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_IronToIron",
        default_stats_table_name="stats_iron_to_iron",
    ),
    "kane": CountyProfile(
        key="kane",
        aliases=["kane"],
        display_name="Kane",
        default_match_fields="STREETNAME STREETNAME",
        default_compare_fields=(
            "PREDIR PREDIR; STREETNAME STREETNAME; STREETTYPE STREETTYPE; SUFDIR SUFDIR; "
            "ACSALIAS ACSALIAS; ALIAS1 ALIAS1; ALIAS1TYPE ALIAS1TYPE; ALIAS2 ALIAS2; ALIAS2TYPE ALIAS2TYPE; "
            "L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD"
        ),
        text_fields=["PREDIR", "STREETNAME", "STREETTYPE", "SUFDIR", "ACSALIAS", "ALIAS1", "ALIAS1TYPE", "ALIAS2", "ALIAS2TYPE"],
        numeric_fields=["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_KaneToKane",
        default_stats_table_name="stats_kane_to_kane",
    ),
    "millard": CountyProfile(
        key="millard",
        aliases=["millard"],
        display_name="Millard",
        default_match_fields="FULLNAME FULLNAME",
        default_compare_fields=(
            "PREDIR PREDIR; FULLNAME FULLNAME; STREETTYPE STREETTYPE; SUFDIR SUFDIR; "
            "ALIAS1 ALIAS1; ALIAS1TYPE ALIAS1TYPE; ALIAS2 ALIAS2; ALIAS2TYPE ALIAS2TYPE; "
            "L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD"
        ),
        text_fields=["PREDIR", "FULLNAME", "STREETTYPE", "SUFDIR", "ALIAS1", "ALIAS1TYPE", "ALIAS2", "ALIAS2TYPE"],
        numeric_fields=["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_MillardToMillard",
        default_stats_table_name="stats_millard_to_millard",
    ),
    "morgan": CountyProfile(
        key="morgan",
        aliases=["morgan"],
        display_name="Morgan",
        default_match_fields="FULLNAME FULLNAME",
        default_compare_fields=(
            "FROMLEFT FROMLEFT; TOLEFT TOLEFT; FROMRIGHT FROMRIGHT; TORIGHT TORIGHT; FULLNAME FULLNAME"
        ),
        text_fields=["FULLNAME"],
        numeric_fields=["FROMLEFT", "TOLEFT", "FROMRIGHT", "TORIGHT"],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_MorganToMorgan",
        default_stats_table_name="new_roads_stats_morgan",
    ),
    "piute": CountyProfile(
        key="piute",
        aliases=["piute"],
        display_name="Piute",
        default_match_fields="NAME NAME",
        default_compare_fields=(
            "PREDIR PREDIR; NAME NAME; POSTTYPE POSTTYPE; POSTDIR POSTDIR; "
            "FROMADDR_L FROMADDR_L; TOADDR_L TOADDR_L; "
            "FROMADDR_R FROMADDR_R; TOADDR_R TOADDR_R"
        ),
        text_fields=["PREDIR", "NAME", "POSTTYPE", "POSTDIR"],
        numeric_fields=["FROMADDR_L", "TOADDR_L", "FROMADDR_R", "TOADDR_R"],
        normalize_mode="strip_blank",
        default_dfc_output_name="DFC_PiuteToPiute",
        default_stats_table_name="new_roads_stats_piute",
    ),
    "rich": CountyProfile(
        key="rich",
        aliases=["rich"],
        display_name="Rich",
        default_match_fields="S_NAME S_NAME",
        default_compare_fields=(
            "PRE_DIR PRE_DIR; S_NAME S_NAME; S_TYPE S_TYPE; SUF_DIR SUF_DIR; "
            "ACS_ALIAS ACS_ALIAS; ALIAS1 ALIAS1; ALIAS1_TYP ALIAS1_TYP; "
            "ALIAS2 ALIAS2; ALIAS2_TYP ALIAS2_TYP; "
            "L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD"
        ),
        text_fields=["PRE_DIR", "S_NAME", "S_TYPE", "SUF_DIR", "ACS_ALIAS", "ALIAS1", "ALIAS1_TYP", "ALIAS2", "ALIAS2_TYP"],
        numeric_fields=["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_RichToRich",
        default_stats_table_name="stats_rich_to_rich",
    ),
    "vecc": CountyProfile(
        key="vecc",
        aliases=["vecc", "saltlake vecc", "salt lake vecc"],
        display_name="Salt Lake VECC",
        default_match_fields="NAME NAME",
        default_compare_fields=(
            "PREDIR PREDIR; NAME NAME; POSTTYPE POSTTYPE; POSTDIR POSTDIR; "
            "AN_NAME AN_NAME; AN_POSTDIR AN_POSTDIR; "
            "FROMADDR_L FROMADDR_L; TOADDR_L TOADDR_L; "
            "FROMADDR_R FROMADDR_R; TOADDR_R TOADDR_R"
        ),
        text_fields=["PREDIR", "NAME", "POSTTYPE", "POSTDIR", "AN_NAME", "AN_POSTDIR"],
        numeric_fields=["FROMADDR_L", "TOADDR_L", "FROMADDR_R", "TOADDR_R"],
        normalize_mode="strip_blank",
        default_dfc_output_name="DFC_VeccToVecc",
        default_stats_table_name="stats_vecc_to_vecc",
    ),
    "sanjuan": CountyProfile(
        key="sanjuan",
        aliases=["sanjuan", "san juan"],
        display_name="San Juan",
        default_match_fields="S_NAME S_NAME",
        default_compare_fields="S_NAME S_NAME",
        text_fields=["S_NAME"],
        numeric_fields=[],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_SanJuanToSanJuan",
        default_stats_table_name="stats_SanJuan_to_SanJuan",
    ),
    "sevier": CountyProfile(
        key="sevier",
        aliases=["sevier"],
        display_name="Sevier",
        default_match_fields="S_NAME S_NAME",
        default_compare_fields=(
            "L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD; "
            "PRE_DIR PRE_DIR; S_NAME S_NAME; S_TYPE S_TYPE; SUR_DIR SUR_DIR; ALIAS ALIAS"
        ),
        text_fields=["PRE_DIR", "S_NAME", "S_TYPE", "SUR_DIR", "ALIAS"],
        numeric_fields=["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_SevierToSevier",
        default_stats_table_name="stats_sevier_to_sevier",
    ),
    "summit": CountyProfile(
        key="summit",
        aliases=["summit"],
        display_name="Summit",
        default_match_fields="STREET STREET",
        default_compare_fields=(
            "PREFIX_DIR PREFIX_DIR; STREET STREET; CLASSIFICA CLASSIFICA; POST_DIR POST_DIR; "
            "FROMLEFT FROMLEFT; TOLEFT TOLEFT; FROMRIGHT FROMRIGHT; TORIGHT TORIGHT"
        ),
        text_fields=["PREFIX_DIR", "STREET", "CLASSIFICA", "POST_DIR"],
        numeric_fields=["FROMLEFT", "TOLEFT", "FROMRIGHT", "TORIGHT"],
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_SummitToSummit",
        default_stats_table_name="stats_summit_to_summit",
    ),
    "tooele": CountyProfile(
        key="tooele",
        aliases=["tooele"],
        display_name="Tooele",
        default_match_fields="FULLNAME FULLNAME",
        default_compare_fields=(
            "FROMADDR_L FROMADDR_L; TOADDR_L TOADDR_L; FROMADDR_R FROMADDR_R; TOADDR_R TOADDR_R; "
            "FULLNAME FULLNAME; PREDIR PREDIR; A1_NAME A1_NAME; A2_NAME A2_NAME; AN_NAME AN_NAME; STATUS STATUS"
        ),
        text_fields=["FULLNAME", "PREDIR", "A1_NAME", "A2_NAME", "AN_NAME", "STATUS"],
        numeric_fields=["FROMADDR_L", "TOADDR_L", "FROMADDR_R", "TOADDR_R"],
        uppercase_normalize_fields={"FULLNAME", "A1_NAME", "A2_NAME"},
        normalize_mode="grand_legacy",
        default_dfc_output_name="DFC_TooeleToTooele",
        default_stats_table_name="new_roads_stats_tooele",
    ),
    "uintah": CountyProfile(
        key="uintah",
        aliases=["uintah"],
        display_name="Uintah",
        default_match_fields="S_NAME S_NAME",
        default_compare_fields=(
            "toleft toleft; toright toright; fromleft fromleft; fromright fromright; S_NAME S_NAME; ALIAS1 ALIAS1"
        ),
        text_fields=["S_NAME", "ALIAS1"],
        numeric_fields=["toleft", "toright", "fromleft", "fromright"],
        uppercase_normalize_fields={"S_NAME", "ALIAS1"},
        normalize_mode="grand_legacy",
        default_dfc_output_name="DFC_UintahToUintah",
        default_stats_table_name="stats_uintah_to_uintah",
    ),
    "utah": CountyProfile(
        key="utah",
        aliases=["utah"],
        display_name="Utah",
        default_match_fields="ROADNAME ROADNAME",
        default_compare_fields=(
            "ROADPREDIR ROADPREDIR; ROADNAME ROADNAME; ROADTYPE ROADTYPE; ROADPOSTDIR ROADPOSTDIR; "
            "ALTROADNAME ALTROADNAME; ALTROADTYPE ALTROADTYPE; ALTROADNAME2 ALTROADNAME2; ALTROADTYPE2 ALTROADTYPE2; "
            "FROMLEFT FROMLEFT; TOLEFT TOLEFT; FROMRIGHT FROMRIGHT; TORIGHT TORIGHT"
        ),
        text_fields=["ROADPREDIR", "ROADNAME", "ROADTYPE", "ROADPOSTDIR", "ALTROADNAME", "ALTROADTYPE", "ALTROADNAME2", "ALTROADTYPE2"],
        numeric_fields=["FROMLEFT", "TOLEFT", "FROMRIGHT", "TORIGHT"],
        normalize_mode="strip_blank",
        default_dfc_output_name="DFC_UtahToUtah",
        default_stats_table_name="stats_utah_to_utah",
    ),
    "wasatch": CountyProfile(
        key="wasatch",
        aliases=["wasatch"],
        display_name="Wasatch",
        default_match_fields="FULLNAME FULLNAME",
        default_compare_fields=(
            "FROMADDR_L FROMADDR_L; TOADDR_L TOADDR_L; FROMADDR_R FROMADDR_R; TOADDR_R TOADDR_R; FULLNAME FULLNAME; PREDIR PREDIR; AN_NAME AN_NAME"
        ),
        text_fields=["FULLNAME", "PREDIR", "AN_NAME", "STATUS"],
        numeric_fields=["FROMADDR_L", "TOADDR_L", "FROMADDR_R", "TOADDR_R"],
        uppercase_normalize_fields={"FULLNAME"},
        normalize_mode="grand_legacy",
        default_dfc_output_name="DFC_WasatchToWasatch",
        default_stats_table_name="stats_wasatch_to_wasatch",
    ),
    "washington": CountyProfile(
        key="washington",
        aliases=["washington"],
        display_name="Washington",
        default_match_fields="NAME NAME",
        default_compare_fields=(
            "FROMADDR_L FROMADDR_L; TOADDR_L TOADDR_L; FROMADDR_R FROMADDR_R; TOADDR_R TOADDR_R; PREDIR PREDIR; NAME NAME; POSTTYPE POSTTYPE; POSTDIR POSTDIR; SUFFIXDIR SUFFIXDIR; "
            "AN_NAME AN_NAME; AN_POSTDIR AN_POSTDIR; A1_NAME A1_NAME; A1_POSTTYPE A1_POSTTYPE; A2_NAME A2_NAME; A2_POSTTYPE A2_POSTTYPE"
        ),
        text_fields=["PREDIR", "NAME", "POSTTYPE", "SUFFIXDIR", "POSTDIR", "AN_NAME", "AN_POSTDIR", "A1_NAME", "A1_POSTTYPE", "A2_NAME", "A2_POSTTYPE"],
        numeric_fields=["FROMADDR_L", "TOADDR_L", "FROMADDR_R", "TOADDR_R"],
        normalize_mode="strip_blank",
        default_dfc_output_name="DFC_WashToWash",
        default_stats_table_name="stats_Wash_to_Wash",
    ),
    "wayne": CountyProfile(
        key="wayne",
        aliases=["wayne"],
        display_name="Wayne",
        default_match_fields="S_NAME S_NAME",
        default_compare_fields=(
            "PRE_DIR PRE_DIR; S_NAME S_NAME; S_TYPE S_TYPE; SUF_DIR SUF_DIR; ACS_ALIAS ACS_ALIAS; ALIAS1 ALIAS1; ALIAS1_TYP ALIAS1_TYP; "
            "L_F_ADD L_F_ADD; L_T_ADD L_T_ADD; R_F_ADD R_F_ADD; R_T_ADD R_T_ADD"
        ),
        text_fields=["PRE_DIR", "S_NAME", "S_TYPE", "SUF_DIR", "ACS_ALIAS", "ALIAS1", "ALIAS1_TYP"],
        numeric_fields=["L_F_ADD", "L_T_ADD", "R_F_ADD", "R_T_ADD"],
        normalize_mode="strip_blank",
        default_dfc_output_name="DFC_WayneToWayne",
        default_stats_table_name="stats_Wayne_to_Wayne",
    ),
    "weber": CountyProfile(
        key="weber",
        aliases=["weber"],
        display_name="Weber",
        default_match_fields="S_NAME S_NAME",
        default_compare_fields=(
            "PREDIR PREDIR; S_NAME S_NAME; STREETTYPE STREETTYPE; SUFDIR SUFDIR; ALIAS ALIAS; ACS_ALIAS ACS_ALIAS; SUFFIX_911 SUFFIX_911; "
            "LEFTFROM LEFTFROM; LEFTTO LEFTTO; RIGHTFROM RIGHTFROM; RIGHTTO RIGHTTO"
        ),
        text_fields=["PREDIR", "S_NAME", "STREETTYPE", "SUFDIR", "ALIAS", "ACS_ALIAS", "SUFFIX_911"],
        numeric_fields=["LEFTFROM", "LEFTTO", "RIGHTFROM", "RIGHTTO"],
        normalize_mode="strip_blank",
        default_dfc_output_name="DFC_WeberToWeber",
        default_stats_table_name="stats_weber_to_weber",
    ),
    "davis": CountyProfile(
        key="davis",
        aliases=["davis"],
        display_name="Davis",
        default_match_fields="RoadName RoadName",
        default_compare_fields=None,
        normalize_mode="single_space_or_null",
        default_dfc_output_name="DFC_DavisToDavis",
        default_stats_table_name="stats_davis_to_davis",
        davis_schemas={
            "legacy": DavisSchema(
                description="Legacy/truncated Davis field names",
                text_fields=["PrefixDire", "RoadName", "RoadNameTy", "PostDirect", "RoadAliasN"],
                numeric_fields=["LeftFrom", "LeftTo", "RightFrom", "RightTo"],
                compare_pairs=[
                    ("PrefixDire", "PrefixDire"),
                    ("RoadName", "RoadName"),
                    ("RoadNameTy", "RoadNameTy"),
                    ("PostDirect", "PostDirect"),
                    ("RoadAliasN", "RoadAliasN"),
                    ("LeftFrom", "LeftFrom"),
                    ("LeftTo", "LeftTo"),
                    ("RightFrom", "RightFrom"),
                    ("RightTo", "RightTo"),
                ],
            ),
            "gdb": DavisSchema(
                description="GDB/full Davis field names",
                text_fields=["PrefixDirection", "RoadName", "RoadNameType", "PostDirection", "RoadAliasName"],
                numeric_fields=["LeftFrom", "LeftTo", "RightFrom", "RightTo", "MPH"],
                compare_pairs=[
                    ("PrefixDirection", "PrefixDirection"),
                    ("RoadName", "RoadName"),
                    ("RoadNameType", "RoadNameType"),
                    ("PostDirection", "PostDirection"),
                    ("RoadAliasName", "RoadAliasName"),
                    ("LeftFrom", "LeftFrom"),
                    ("LeftTo", "LeftTo"),
                    ("RightFrom", "RightFrom"),
                    ("RightTo", "RightTo"),
                    ("MPH", "MPH"),
                ],
            ),
        },
    ),
}


def log(message):
    print(message)


def get_field_name_map(feature_class):
    return {field.name.lower(): field.name for field in arcpy.ListFields(feature_class)}


def ensure_detect_feature_changes_license():
    product_info = str(arcpy.ProductInfo()).strip()
    if product_info.lower() in {"arcinfo", "advanced"}:
        return
    arcinfo_status = str(arcpy.CheckProduct("ArcInfo")).strip()
    raise RuntimeError(
        "Detect Feature Changes requires an ArcGIS Pro Advanced license. "
        f"Current ProductInfo is '{product_info}' and CheckProduct('ArcInfo') is "
        f"'{arcinfo_status}'. Ask your GIS admin to assign an Advanced seat, then rerun this script."
    )


def parse_field_pairs(field_mapping):
    pairs = []
    for token in field_mapping.split(";"):
        parts = token.strip().split()
        if len(parts) >= 2:
            pairs.append((parts[0], parts[1]))
    return pairs


def resolve_field_pairs(update_features, base_features, field_mapping):
    update_map = get_field_name_map(update_features)
    base_map = get_field_name_map(base_features)
    resolved_pairs = []
    for update_field, base_field in parse_field_pairs(field_mapping):
        update_actual = update_map.get(update_field.lower())
        base_actual = base_map.get(base_field.lower())
        if update_actual and base_actual:
            resolved_pairs.append((update_actual, base_actual))
    return resolved_pairs


def get_output_workspace(update_features):
    dirname = os.path.dirname(arcpy.Describe(update_features).catalogPath)
    desc = arcpy.Describe(dirname)
    if hasattr(desc, "datasetType") and desc.datasetType == "FeatureDataset":
        dirname = os.path.dirname(dirname)
    return dirname


def _normalize_text_value(value, force_uppercase):
    if value in ("", " ", "None", "NULL", None):
        return ""
    if force_uppercase:
        return " ".join(str(value).split()).upper()
    return value


def normalize_fields(feature_class, profile, text_fields=None, numeric_fields=None):
    field_map = get_field_name_map(feature_class)
    text_source = text_fields if text_fields is not None else profile.text_fields
    numeric_source = numeric_fields if numeric_fields is not None else profile.numeric_fields

    text_existing = [field_map[name.lower()] for name in text_source if name.lower() in field_map]
    numeric_existing = [field_map[name.lower()] for name in numeric_source if name.lower() in field_map]
    field_names = text_existing + numeric_existing

    if not field_names:
        return

    with arcpy.da.UpdateCursor(feature_class, field_names) as rows:
        for row in rows:
            updated = False
            for idx in range(len(text_existing)):
                value = row[idx]
                replacement = value
                if profile.normalize_mode == "single_space_or_null":
                    if value == " " or value is None:
                        replacement = ""
                elif profile.normalize_mode == "grand_legacy":
                    field_name = text_existing[idx]
                    replacement = _normalize_text_value(
                        value,
                        force_uppercase=field_name.upper() in profile.uppercase_normalize_fields,
                    )
                else:
                    if value is None or str(value).strip() == "":
                        replacement = ""

                if replacement != value:
                    row[idx] = replacement
                    updated = True

            for idx in range(len(text_existing), len(field_names)):
                value = row[idx]
                replacement = value
                if profile.normalize_mode == "single_space_or_null":
                    if value == " " or value is None:
                        replacement = 0
                else:
                    if value is None or str(value).strip() == "":
                        replacement = 0

                if replacement != value:
                    row[idx] = replacement
                    updated = True

            if updated:
                rows.updateRow(row)


def resolve_county_profile(county):
    county_key = county.lower().strip()
    for profile in PROFILES.values():
        aliases = {alias.lower() for alias in profile.aliases}
        aliases.add(profile.key.lower())
        if county_key in aliases:
            return profile
    raise RuntimeError(f"Unknown county '{county}'. Supported counties: {', '.join(sorted(PROFILES.keys()))}")


def resolve_feature_inputs(args):
    if not args.update_features or not args.base_features:
        raise RuntimeError(
            "Missing required input paths. Provide both --update-features and --base-features."
        )
    return args.update_features, args.base_features


def _resolve_davis_schema(profile, schema_option, update_features, base_features):
    if not profile.davis_schemas:
        return None, None

    def _has_all_fields(feature_class, required_fields):
        lookup = get_field_name_map(feature_class)
        return all(field_name.lower() in lookup for field_name in required_fields)

    if schema_option in profile.davis_schemas:
        requested = profile.davis_schemas[schema_option]
        required = requested.text_fields + requested.numeric_fields
        if _has_all_fields(update_features, required) and _has_all_fields(base_features, required):
            return schema_option, requested
        raise RuntimeError(
            f"Requested schema '{schema_option}' but required fields are missing in one or both inputs."
        )

    gdb_schema = profile.davis_schemas["gdb"]
    legacy_schema = profile.davis_schemas["legacy"]

    if _has_all_fields(update_features, gdb_schema.text_fields) and _has_all_fields(base_features, gdb_schema.text_fields):
        return "gdb", gdb_schema

    if _has_all_fields(update_features, legacy_schema.text_fields) and _has_all_fields(base_features, legacy_schema.text_fields):
        return "legacy", legacy_schema

    raise RuntimeError("Could not auto-detect Davis schema. Use --schema legacy or --schema gdb.")


def run_change_detection(
    profile,
    update_features,
    base_features,
    search_distance,
    match_fields,
    change_tolerance,
    compare_fields,
    dfc_output_name,
    stats_table_name,
    recents_name,
    schema_option="auto",
):
    arcpy.env.overwriteOutput = True
    output_workspace = get_output_workspace(update_features)
    dfc_output = os.path.join(output_workspace, dfc_output_name)
    stats_table = os.path.join(output_workspace, stats_table_name)
    out_feature = os.path.join(output_workspace, recents_name)

    active_text_fields = profile.text_fields
    active_numeric_fields = profile.numeric_fields

    if profile.key == "davis":
        schema_name, schema = _resolve_davis_schema(profile, schema_option, update_features, base_features)
        active_text_fields = schema.text_fields
        active_numeric_fields = schema.numeric_fields
        if not compare_fields:
            update_lookup = get_field_name_map(update_features)
            base_lookup = get_field_name_map(base_features)
            compare_parts = []
            for update_field, base_field in schema.compare_pairs:
                u = update_lookup.get(update_field.lower())
                b = base_lookup.get(base_field.lower())
                if u and b:
                    compare_parts.append(f"{u} {b}")
            if not compare_parts:
                raise RuntimeError("No comparable fields were found for Detect Feature Changes.")
            compare_fields = "; ".join(compare_parts)
        log(f"Using Davis schema: {schema_name} ({schema.description})")

    if not compare_fields:
        raise RuntimeError("Compare fields were not provided and county profile has no default compare mapping.")

    resolved_match_pairs = resolve_field_pairs(update_features, base_features, match_fields)
    if not resolved_match_pairs:
        raise RuntimeError(
            "No valid match field pairs found between update and base feature classes. "
            "Pass --match-fields with fields that exist in both datasets."
        )
    match_fields = "; ".join([f"{update_field} {base_field}" for update_field, base_field in resolved_match_pairs])

    resolved_compare_pairs = resolve_field_pairs(update_features, base_features, compare_fields)
    if not resolved_compare_pairs:
        raise RuntimeError(
            "No valid compare field pairs found between update and base feature classes. "
            "Pass --compare-fields with fields that exist in both datasets."
        )
    compare_fields = "; ".join([f"{update_field} {base_field}" for update_field, base_field in resolved_compare_pairs])

    log("begin converting nulls to empty")
    for feature_class in [update_features, base_features]:
        normalize_fields(
            feature_class,
            profile,
            text_fields=active_text_fields,
            numeric_fields=active_numeric_fields,
        )

    log("begin detect feature changes")
    log(f"Beginning detect feature change process for {profile.display_name} at: {time.strftime('%c')}")
    arcpy.management.DetectFeatureChanges(
        update_features,
        base_features,
        dfc_output,
        search_distance,
        match_fields,
        stats_table,
        change_tolerance,
        compare_fields,
    )
    log("finished detect feature change process")

    log(f"begin creating separate feature class named {recents_name}")
    arcpy.env.qualifiedFieldNames = False

    roads_layer = "roads_lyr"
    dfc_layer = "dfc_lyr"
    arcpy.management.MakeFeatureLayer(update_features, roads_layer)
    arcpy.management.MakeFeatureLayer(dfc_output, dfc_layer)

    join_field_roads = arcpy.Describe(roads_layer).OIDFieldName
    arcpy.management.AddJoin(roads_layer, join_field_roads, dfc_layer, "UPDATE_FID")

    dfc_name = arcpy.Describe(dfc_output).name
    expression = f"{dfc_name}.CHANGE_TYPE <> 'NC'"
    arcpy.management.SelectLayerByAttribute(roads_layer, "NEW_SELECTION", expression)
    arcpy.management.CopyFeatures(roads_layer, out_feature)

    log("Finished detect feature change process at: " + time.strftime("%c"))
    log("done at: " + time.strftime("%c"))


def build_parser():
    parser = argparse.ArgumentParser(
        description="Detect recent edits between county update and baseline roads.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python Get_Recent_Edits.py --county Grand "
            "--update-features \"Z:\\Documents\\gdb\\GRAND\\GrandCo_20260514.gdb\\GC__RDS_05_01_26\" "
            "--base-features \"Z:\\Documents\\gdb\\GRAND\\GrandCo_20240812.gdb\\GRANDROADS_24\"\n"
            "\n"
            "  python Get_Recent_Edits.py --county Davis "
            "--update-features \"Z:\\Documents\\gdb\\DavisCounty_20260626.gdb\\DavisRoads\" "
            "--base-features \"Z:\\Documents\\gdb\\DavisCounty_20260604.gdb\\DavisRoads\""
        ),
    )
    parser.add_argument("--county", required=True, help="County key, such as Beaver, BoxElder, Cache, Daggett, Duchesne, Emery, Grand, Garfield, Carbon, Iron, Kane, Millard, Morgan, Piute, Rich, SanJuan, Sevier, Summit, Tooele, Uintah, Utah, Wasatch, Washington, Wayne, Weber, vecc, or Davis.")

    parser.add_argument("--update-features", required=True, help="Full path to newest county road feature class.")
    parser.add_argument("--base-features", required=True, help="Full path to previous county road feature class.")

    parser.add_argument(
        "--schema",
        default="auto",
        choices=["auto", "legacy", "gdb"],
        help="Schema mode for counties that support it (currently Davis).",
    )

    parser.add_argument(
        "--search-distance",
        default="200 Feet",
        help="Search distance for candidate matches in Detect Feature Changes.",
    )
    parser.add_argument("--match-fields", help="Semicolon-delimited field mapping string used for matching.")
    parser.add_argument("--change-tolerance", default="40", help="Change tolerance used by Detect Feature Changes.")
    parser.add_argument(
        "--compare-fields",
        help=(
            "Optional semicolon-delimited field mapping string for compare attributes. "
            "When omitted, county defaults are used."
        ),
    )
    parser.add_argument("--dfc-output-name", help="Output feature class name for Detect Feature Changes result.")
    parser.add_argument("--stats-table-name", help="Output table name for Detect Feature Changes statistics.")
    parser.add_argument("--recents-name", help="Output feature class name for selected changed roads.")
    return parser


def main(argv=None):
    start_time = time.time()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        profile = resolve_county_profile(args.county)
        update_features, base_features = resolve_feature_inputs(args)

        ensure_detect_feature_changes_license()

        match_fields = args.match_fields or profile.default_match_fields
        compare_fields = args.compare_fields if args.compare_fields is not None else profile.default_compare_fields
        dfc_output_name = args.dfc_output_name or profile.default_dfc_output_name
        stats_table_name = args.stats_table_name or profile.default_stats_table_name
        recents_name = args.recents_name or profile.default_recents_name

        run_change_detection(
            profile=profile,
            update_features=update_features,
            base_features=base_features,
            search_distance=args.search_distance,
            match_fields=match_fields,
            change_tolerance=args.change_tolerance,
            compare_fields=compare_fields,
            dfc_output_name=dfc_output_name,
            stats_table_name=stats_table_name,
            recents_name=recents_name,
            schema_option=args.schema,
        )
    except RuntimeError as exc:
        log(str(exc))
        return 2

    elapsed = time.time() - start_time
    log("Time elapsed: {:.2f}s".format(elapsed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
