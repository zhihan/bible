// Library to interact with api.lsm.org/recver.php

const http = require('http');
const baseurl = "http://api.lsm.org/recver.php?";

async function fetch_verses(verse) {
    return new Promise((resolve, reject) => {
        const url = baseurl + "String=" + verse + "&Out=json";
        http.get(url, (response) => {
        let data = "";
        if (response.statusCode !== 200) {
            reject(new Error(`HTTP error! Status: ${response.statusCode}`));
            return;
        }
        response.on("data", (chunk) => {
            data += chunk;
        });
        response.on("end", () => {
            resolve(data);
        });
    }).on('error', (e) => {
        reject(e);
    });
    })
}


module.exports = { fetch_verses }
