"""Send premade emails to a list of recipients via SMTP."""
import argparse
import csv
import os
import re
import smtplib
import ssl
import sys
import time
from email.message import EmailMessage
from pathlib import Path

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def load_env_file(env_path):
    if not env_path:
        return
    env_path = Path(env_path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_setting(cli_value, env_key, default=None):
    if cli_value is not None:
        return cli_value
    if env_key:
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
    return default


def normalize_row(row):
    data = {}
    for key, value in row.items():
        if key is None:
            continue
        clean_key = key.strip()
        if not clean_key:
            continue
        clean_value = (value or "").strip()
        data[clean_key] = clean_value
        data[clean_key.lower()] = clean_value
    return data


def parse_csv_recipients(path):
    recipients = []
    with open(path, newline="", encoding="utf-8") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel

        try:
            has_header = csv.Sniffer().has_header(sample)
        except csv.Error:
            has_header = False

        reader = csv.reader(handle, dialect)
        try:
            first_row = next(reader)
        except StopIteration:
            return recipients

        header_candidates = {cell.strip().lower() for cell in first_row if cell}
        detected_header = bool(header_candidates & {"email", "e-mail", "name", "brand"})
        if has_header or detected_header:
            fieldnames = [cell.strip() for cell in first_row]
            dict_reader = csv.DictReader(handle, fieldnames=fieldnames, dialect=dialect)
            for row in dict_reader:
                data = normalize_row(row)
                recipients.append(data)
        else:
            rows = [first_row]
            rows.extend(reader)
            for row in rows:
                if not row:
                    continue
                email = row[0].strip()
                name = row[1].strip() if len(row) > 1 else ""
                brand = row[2].strip() if len(row) > 2 else ""
                recipients.append({"email": email, "name": name, "brand": brand})
    return recipients


def parse_line_recipients(path):
    recipients = []
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        email = line
        name = ""
        if "," in line:
            parts = [part.strip() for part in line.split(",", 1)]
            email = parts[0]
            name = parts[1] if len(parts) > 1 else ""
        recipients.append({"email": email, "name": name})
    return recipients


def parse_recipients(path):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return parse_csv_recipients(path)
    return parse_line_recipients(path)


def find_subject_from_template(text_body):
    lines = text_body.splitlines()
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            body = "\n".join(lines[idx + 1 :]).lstrip("\n")
            return subject, body
        break
    return None, text_body


def render_template(template_text, data):
    return template_text.format_map(SafeDict(data))


def build_message(from_email, from_name, to_email, subject, text_body, html_body, reply_to):
    message = EmailMessage()
    if from_name:
        message["From"] = f"{from_name} <{from_email}>"
    else:
        message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    if reply_to:
        message["Reply-To"] = reply_to

    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")
    return message


def main():
    parser = argparse.ArgumentParser(
        description="Send a premade email to a list of recipients."
    )
    parser.add_argument("--recipients", required=True, help="CSV or TXT list of emails.")
    parser.add_argument("--template", required=True, help="Text template file.")
    parser.add_argument("--html-template", help="Optional HTML template file.")
    parser.add_argument("--subject", help="Email subject (overrides Subject: in template).")
    parser.add_argument("--from-email", help="From email address.")
    parser.add_argument("--from-name", help="From name.")
    parser.add_argument("--reply-to", help="Reply-To email address.")
    parser.add_argument("--smtp-host", help="SMTP host.")
    parser.add_argument("--smtp-port", type=int, help="SMTP port.")
    parser.add_argument("--smtp-user", help="SMTP username.")
    parser.add_argument("--smtp-password", help="SMTP password.")
    parser.add_argument("--ssl", action="store_true", help="Use SMTP over SSL (port 465).")
    parser.add_argument(
        "--no-starttls",
        action="store_true",
        help="Disable STARTTLS (for servers that do not support it).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending.")
    parser.add_argument("--limit", type=int, help="Send only the first N emails.")
    parser.add_argument("--sleep", type=float, default=0, help="Seconds to sleep per email.")
    parser.add_argument("--env", help="Optional .env file to load SMTP_* values from.")
    parser.add_argument(
        "--skip-invalid",
        action="store_true",
        help="Skip invalid emails instead of exiting.",
    )

    args = parser.parse_args()

    load_env_file(args.env)

    smtp_host = get_setting(args.smtp_host, "SMTP_HOST")
    smtp_port = get_setting(args.smtp_port, "SMTP_PORT")
    smtp_user = get_setting(args.smtp_user, "SMTP_USERNAME")
    smtp_password = get_setting(args.smtp_password, "SMTP_PASSWORD")
    from_email = get_setting(args.from_email, "SMTP_FROM") or smtp_user
    from_name = get_setting(args.from_name, "SMTP_FROM_NAME", "")
    reply_to = get_setting(args.reply_to, "SMTP_REPLY_TO", "")
    subject_override = get_setting(args.subject, "EMAIL_SUBJECT")

    if not smtp_host:
        print("SMTP host is required. Use --smtp-host or SMTP_HOST.", file=sys.stderr)
        sys.exit(1)
    if not from_email:
        print("From email is required. Use --from-email or SMTP_FROM.", file=sys.stderr)
        sys.exit(1)

    if smtp_port is None:
        smtp_port = 465 if args.ssl else 587
    else:
        smtp_port = int(smtp_port)

    text_template = Path(args.template).read_text(encoding="utf-8")
    subject_from_template, text_body = find_subject_from_template(text_template)
    subject_template = subject_override or subject_from_template
    if not subject_template:
        print(
            "Subject is required. Use --subject or include 'Subject:' in template.",
            file=sys.stderr,
        )
        sys.exit(1)

    html_body = None
    if args.html_template:
        html_template = Path(args.html_template).read_text(encoding="utf-8")
    else:
        html_template = None

    recipients = parse_recipients(args.recipients)
    if args.limit:
        recipients = recipients[: args.limit]

    if not recipients:
        print("No recipients found.", file=sys.stderr)
        sys.exit(1)

    invalid_emails = []
    for recipient in recipients:
        email = recipient.get("email") or recipient.get("Email") or recipient.get("e-mail")
        if not email or not EMAIL_RE.match(email):
            invalid_emails.append(email or "<missing>")

    if invalid_emails:
        message = f"Invalid emails: {', '.join(invalid_emails[:10])}"
        if len(invalid_emails) > 10:
            message += f" (and {len(invalid_emails) - 10} more)"
        if args.skip_invalid:
            print(message, file=sys.stderr)
        else:
            print(message, file=sys.stderr)
            sys.exit(1)

    if args.dry_run:
        print(f"Dry run: {len(recipients)} emails ready.")
        print(f"Subject template: {subject_template}")
        if recipients:
            sample_data = normalize_row(recipients[0])
            sample_data.setdefault(
                "email",
                recipients[0].get("email")
                or recipients[0].get("Email")
                or recipients[0].get("e-mail"),
            )
            sample_data.setdefault("name", sample_data.get("name", ""))
            print(f"Subject example: {render_template(subject_template, sample_data)}")
        print("First 5 recipients:")
        for recipient in recipients[:5]:
            email = recipient.get("email") or recipient.get("Email") or recipient.get("e-mail")
            name = recipient.get("name") or recipient.get("Name") or ""
            print(f"  {email} ({name})")
        return

    context = ssl.create_default_context()

    if args.ssl:
        smtp = smtplib.SMTP_SSL(smtp_host, smtp_port, context=context)
    else:
        smtp = smtplib.SMTP(smtp_host, smtp_port)

    with smtp:
        smtp.ehlo()
        if not args.ssl and not args.no_starttls:
            smtp.starttls(context=context)
            smtp.ehlo()

        if smtp_user and smtp_password:
            smtp.login(smtp_user, smtp_password)

        sent = 0
        failed = 0
        for recipient in recipients:
            email = recipient.get("email") or recipient.get("Email") or recipient.get("e-mail")
            if not email or not EMAIL_RE.match(email):
                if args.skip_invalid:
                    continue
                raise ValueError(f"Invalid email: {email}")

            data = normalize_row(recipient)
            data.setdefault("email", email)
            data.setdefault("name", data.get("name", ""))

            rendered_text = render_template(text_body, data)
            rendered_html = render_template(html_template, data) if html_template else None
            rendered_subject = render_template(subject_template, data)

            message = build_message(
                from_email=from_email,
                from_name=from_name,
                to_email=email,
                subject=rendered_subject,
                text_body=rendered_text,
                html_body=rendered_html,
                reply_to=reply_to,
            )
            try:
                smtp.send_message(message)
                sent += 1
                print(f"Sent to {email}")
            except smtplib.SMTPException as exc:
                failed += 1
                print(f"Failed to send to {email}: {exc}", file=sys.stderr)

            if args.sleep:
                time.sleep(args.sleep)

    print(f"Done. Sent: {sent}. Failed: {failed}.")


if __name__ == "__main__":
    main()
