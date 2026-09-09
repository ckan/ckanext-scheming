const path = require("path");
const { src, watch, dest } = require("gulp");
const sass = require("gulp-sass")(require("sass"));
const if_ = require("gulp-if");
const sourcemaps = require("gulp-sourcemaps");
const rename = require("gulp-rename");

const with_sourcemaps = () => !!process.env.DEBUG;

const DYNAMIC_SCHEMING_SCSS = path.join(
  __dirname, "ckanext/scheming_dynamic/assets/scss"
);
const DYNAMIC_SCHEMING_CSS = path.join(
  __dirname, "ckanext/scheming_dynamic/assets/css"
);

const buildDynamicScheming = () =>
  src(DYNAMIC_SCHEMING_SCSS + "/*.scss")
    .pipe(if_(with_sourcemaps(), sourcemaps.init()))
    .pipe(sass({ outputStyle: "compressed" }).on("error", sass.logError))
    .pipe(if_(with_sourcemaps(), sourcemaps.write()))
    .pipe(rename({ extname: ".css" }))
    .pipe(dest(DYNAMIC_SCHEMING_CSS));

const watchDynamicScheming = () =>
  watch(
    DYNAMIC_SCHEMING_SCSS + "/**/*.scss",
    { ignoreInitial: false },
    buildDynamicScheming
  );

exports.buildDynamicScheming = buildDynamicScheming;
exports.watchDynamicScheming = watchDynamicScheming;
