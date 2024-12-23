#!/usr/bin/env node
// cli.js

const lsm = require("./lsm.js");

const args = process.argv.slice(2);
if (args.length === 0) {
  (async () =>{
  const resp = await lsm.fetch_verses("John 3:16");
  console.log(resp);
  })();
}
