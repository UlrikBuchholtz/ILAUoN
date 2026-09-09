// Run against a disposable source tree, never the installed MathBox checkout.
const fs = require('fs');
const path = require('path');
const {createRequire} = require('module');
const {Transform} = require('stream');
const tools = createRequire(path.join(process.argv[2], 'package.json'));
const coffee = tools('coffee-script');

if (process.argv[3] === 'coffee') {
  process.stdout.write(coffee.compile(fs.readFileSync(0, 'utf8'), {
    bare: process.argv[4] === 'bare', header: false,
  }));
} else {
  const stage = process.argv[3];
  tools('browserify')({
    entries: [path.join(stage, 'mathbox/src/index.coffee')],
    basedir: stage,
    extensions: ['.coffee'],
    paths: [path.join(process.argv[2], 'node_modules')],
    debug: false,
    // Modern Browserify's bare mode omits stream shims used by cssauron.
  }).transform(function (file) {
    let source = '';
    return new Transform({
      transform(chunk, encoding, callback) { source += chunk; callback(); },
      flush(callback) {
        try {
          this.push(file.endsWith('.coffee')
            ? coffee.compile(source, {bare: true, header: false, filename: file})
            : source);
          callback();
        } catch (error) { callback(error); }
      },
    });
  }).bundle(function (error, buffer) {
    if (error) { console.error(error); process.exitCode = 1; }
    else fs.writeFileSync(path.join(stage, 'mathbox/build/mathbox-core.js'), buffer);
  });
}
