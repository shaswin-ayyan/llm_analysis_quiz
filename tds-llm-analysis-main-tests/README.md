# Demo setup

## First, let's give students a demo evaluator

Students should send themselves this POST request.

```json
{
  "email": "student@example.com",
  "secret": "...",
  "url": "https://tds-llm-analysis.s-anand.net/demo"
}
```

Their script should then send a GET request to the `/demo` endpoint.

The `/demo` endpoint will contain a JS-generated version of this text:

> POST this JSON to `https://tds-llm-analysis.s-anand.net/submit`
>
> ```json
> {
>   "email": "your-email",
>   "secret": "your-secret",
>   "url": "https://tds-llm-analysis.s-anand.net/demo",
>   "answer": "anything you want"
> }
> ```

Based on this, the student will send a POST request to `/submit` that looks like the above.

The `/submit` endpoint will always record the request body along with timestamp and IP and run url-specific checks.
The `/demo` URL will return the following JSON:

```jsonc
{
  "correct": true, // if the "answer" key exists, else false
  "url": "https://tds-llm-analysis.s-anand.net/demo-js-scraping?email=<student_email>" // next step
}
```

## Next, let's have the students do JS scraping

The `/demo-js-scraping` endpoint will be a static HTML page that:

- Is rendered using obfuscated JavaScript (e.g. atob / btoa)
- Asks them to scrape `/demo-js-scraping-data?email=<student_email>` to get a secret code
- POST the secret code back to `/submit` along with their email, secret, and url

The `/demo-js-scraping-data` endpoint will be a static HTML page that renders the SHA1 hash of the student's email address.

Based on the student should submit the response to `/submit`.

The `/submit` endpoint will check that the "answer" key matches the SHA1 hash of the student's email address and point them to the next step:

```jsonc
{
  "correct": true, // if the "answer" key matches the SHA1 hash of their email, else false
  "url": "https://tds-llm-analysis.s-anand.net/demo-audio"
}
```

## Now, students will process audio

The `/demo-audio` endpoint will be a static HTML file that asks them to:

- Follow the instructions in `https://tds-llm-analysis.s-anand.net/demo-audio.opus`
- ... which asks them to add all values in the first column of `/demo-audio-data.csv` where the first column is greater than the number provided in the HTML file
- ... and POST the sum back to `/submit` along with their email, secret, and url
  ...

`/demo-audio` also provides them a number derived from their email address in the HTML (e.g. the integer SHA1 hash of their email modulo 1000)

The `/demo-audio-data.csv` endpoint will be a static CSV file with two columns of random integers.

Based on the student should submit the response to `/submit`.

The `/submit` endpoint will check that the "answer" key matches the correct sum and have no further URLs:

```jsonc
{
  "correct": true // if the "answer" key matches the correct sum, else false
}
```

# Setup

First, create the database tables.

```bash
npm install
npx wrangler d1 create tds-llm-analysis
```

Note the UUID and update [`wrangler.toml`](./wrangler.toml) with it. For example:

```toml
[[d1_databases]]
binding = "tds_llm_analysis"
database_name = "tds-llm-analysis"
database_id = "<UUID from above>"
```

Then create the necessary tables in the D1 database.

```bash
# This runs locally. Add --remote to run on CloudFlare D1
npx wrangler d1 migrations apply tds-llm-analysis
```

We can query the database using:

```bash
npx wrangler d1 execute tds-llm-analysis --command "SELECT * FROM submit LIMIT 10;"
```

```bash
npx wrangler d1 execute tds-llm-analysis --remote --json --command "
SELECT
  email,
  CASE
    WHEN instr(url, '?') > 0 THEN substr(url, 1, instr(url, '?') - 1)
    ELSE url
  END AS base_url,
  max(correct) AS score
FROM submit
WHERE timestamp >= '2025-11-25T00:00:00+0530'
  AND timestamp <= '2025-11-25T16:05:00+0530'
  AND delay > 0
  AND delay < 300
  AND email LIKE '%study.iitm.ac.in'
  AND secret
GROUP BY
  email,
  base_url;
" | jq -r '.[].results[] | [.score, .email, .base_url] | @tsv'
```

Run locally via:

```bash
npm run dev
```

Visit the page at `http://localhost:8787/demo` to test.

To deploy, run:

```bash
npx wrangler deploy
```

This is deployed at `https://tds-llm-analysis.s-anand.net/`.
