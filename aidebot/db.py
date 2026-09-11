from __future__ import annotations

import os
import time
from typing import Any

import aiosqlite


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS profiles (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reputation INTEGER NOT NULL DEFAULT 0,
                helped_count INTEGER NOT NULL DEFAULT 0,
                trainings_completed INTEGER NOT NULL DEFAULT 0,
                reviews_count INTEGER NOT NULL DEFAULT 0,
                rating_sum INTEGER NOT NULL DEFAULT 0,
                helper_available INTEGER NOT NULL DEFAULT 0,
                skills TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                training_key TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT '',
                objective TEXT NOT NULL DEFAULT '',
                availability TEXT NOT NULL DEFAULT '',
                budget TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                trainer_id INTEGER,
                progress INTEGER NOT NULL DEFAULT 0,
                total_steps INTEGER NOT NULL DEFAULT 1,
                channel_id INTEGER,
                scheduled_for TEXT,
                payment_status TEXT NOT NULL DEFAULT 'not_required',
                invite_used INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                request_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                UNIQUE(guild_id, request_id, author_id)
            );
            CREATE TABLE IF NOT EXISTS invite_credits (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                credits INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS pending_invites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                inviter_id INTEGER NOT NULL,
                invitee_id INTEGER NOT NULL,
                validate_after INTEGER NOT NULL,
                state TEXT NOT NULL DEFAULT 'pending',
                UNIQUE(guild_id, invitee_id)
            );
            CREATE TABLE IF NOT EXISTS favorites (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                resource_key TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY (guild_id, user_id, resource_key)
            );
            CREATE TABLE IF NOT EXISTS challenge_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                challenge_key TEXT NOT NULL,
                proof TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                reviewer_id INTEGER,
                created_at INTEGER NOT NULL,
                UNIQUE(guild_id, user_id, challenge_key, status)
            );
            CREATE TABLE IF NOT EXISTS mentorships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                mentor_id INTEGER,
                topic TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                target_role TEXT NOT NULL,
                experience TEXT NOT NULL DEFAULT '',
                skills TEXT NOT NULL DEFAULT '',
                availability TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                reviewer_id INTEGER,
                review_reason TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS applications_one_pending_per_user
                ON applications(guild_id, user_id) WHERE status='pending';
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                request_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                trainer_id INTEGER,
                remind_at INTEGER NOT NULL,
                state TEXT NOT NULL DEFAULT 'pending',
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS reminders_due_idx ON reminders(state, remind_at);
            """
        )
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()
            self.conn = None

    def _db(self) -> aiosqlite.Connection:
        if self.conn is None:
            raise RuntimeError("Database not connected")
        return self.conn

    async def ensure_profile(self, guild_id: int, user_id: int) -> None:
        await self._db().execute("INSERT OR IGNORE INTO profiles(guild_id,user_id) VALUES (?,?)", (guild_id, user_id))
        await self._db().commit()

    async def profile(self, guild_id: int, user_id: int) -> aiosqlite.Row:
        await self.ensure_profile(guild_id, user_id)
        cur = await self._db().execute("SELECT * FROM profiles WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        row = await cur.fetchone()
        assert row is not None
        return row

    async def set_helper_available(self, guild_id: int, user_id: int, available: bool) -> None:
        await self.ensure_profile(guild_id, user_id)
        await self._db().execute("UPDATE profiles SET helper_available=? WHERE guild_id=? AND user_id=?", (1 if available else 0, guild_id, user_id))
        await self._db().commit()

    async def available_helpers(self, guild_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        cur = await self._db().execute(
            "SELECT * FROM profiles WHERE guild_id=? AND helper_available=1 ORDER BY reputation DESC, helped_count DESC LIMIT ?",
            (guild_id, limit),
        )
        return list(await cur.fetchall())

    async def add_skill(self, guild_id: int, user_id: int, skill: str) -> None:
        row = await self.profile(guild_id, user_id)
        skills = {s.strip() for s in row["skills"].split(",") if s.strip()}
        skills.add(skill.strip().lower())
        await self._db().execute("UPDATE profiles SET skills=? WHERE guild_id=? AND user_id=?", (",".join(sorted(skills)), guild_id, user_id))
        await self._db().commit()

    async def add_reputation(self, guild_id: int, user_id: int, amount: int) -> None:
        await self.ensure_profile(guild_id, user_id)
        await self._db().execute("UPDATE profiles SET reputation=reputation+? WHERE guild_id=? AND user_id=?", (amount, guild_id, user_id))
        await self._db().commit()

    async def create_request(self, **values: Any) -> int:
        now = int(time.time())
        cur = await self._db().execute(
            """INSERT INTO requests(guild_id,user_id,training_key,level,objective,availability,budget,status,total_steps,payment_status,invite_used,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                values["guild_id"], values["user_id"], values["training_key"], values.get("level", ""),
                values.get("objective", ""), values.get("availability", ""), values.get("budget", ""),
                values.get("status", "open"), values.get("total_steps", 1), values.get("payment_status", "not_required"),
                1 if values.get("invite_used") else 0, now,
            ),
        )
        await self._db().commit()
        return int(cur.lastrowid)

    async def set_request_channel(self, request_id: int, channel_id: int) -> None:
        await self._db().execute("UPDATE requests SET channel_id=? WHERE id=?", (channel_id, request_id))
        await self._db().commit()

    async def request_by_channel(self, channel_id: int) -> aiosqlite.Row | None:
        cur = await self._db().execute("SELECT * FROM requests WHERE channel_id=? ORDER BY id DESC LIMIT 1", (channel_id,))
        return await cur.fetchone()

    async def request_by_id(self, request_id: int) -> aiosqlite.Row | None:
        cur = await self._db().execute("SELECT * FROM requests WHERE id=?", (request_id,))
        return await cur.fetchone()

    async def update_request(self, request_id: int, **fields: Any) -> None:
        allowed = {"status", "trainer_id", "progress", "scheduled_for", "payment_status"}
        safe = {k: v for k, v in fields.items() if k in allowed}
        if not safe:
            return
        sql = ", ".join(f"{k}=?" for k in safe)
        await self._db().execute(f"UPDATE requests SET {sql} WHERE id=?", (*safe.values(), request_id))
        await self._db().commit()

    async def add_invite_credit(self, guild_id: int, user_id: int, amount: int = 1) -> None:
        await self._db().execute(
            """INSERT INTO invite_credits(guild_id,user_id,credits) VALUES (?,?,?)
               ON CONFLICT(guild_id,user_id) DO UPDATE SET credits=credits+excluded.credits""",
            (guild_id, user_id, amount),
        )
        await self._db().commit()

    async def invite_credits(self, guild_id: int, user_id: int) -> int:
        cur = await self._db().execute("SELECT credits FROM invite_credits WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        row = await cur.fetchone()
        return int(row["credits"]) if row else 0

    async def validated_invites(self, guild_id: int, user_id: int) -> int:
        cur = await self._db().execute("SELECT COUNT(*) AS total FROM pending_invites WHERE guild_id=? AND inviter_id=? AND state='valid'", (guild_id, user_id))
        row = await cur.fetchone()
        return int(row["total"]) if row else 0

    async def consume_invite_credit(self, guild_id: int, user_id: int) -> bool:
        await self._db().execute("BEGIN IMMEDIATE")
        cur = await self._db().execute("SELECT credits FROM invite_credits WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        row = await cur.fetchone()
        if not row or row["credits"] <= 0:
            await self._db().rollback()
            return False
        await self._db().execute("UPDATE invite_credits SET credits=credits-1 WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        await self._db().commit()
        return True

    async def add_pending_invite(self, guild_id: int, inviter_id: int, invitee_id: int, validate_after: int) -> None:
        await self._db().execute(
            "INSERT OR IGNORE INTO pending_invites(guild_id,inviter_id,invitee_id,validate_after) VALUES (?,?,?,?)",
            (guild_id, inviter_id, invitee_id, validate_after),
        )
        await self._db().commit()

    async def due_pending_invites(self, now: int) -> list[aiosqlite.Row]:
        cur = await self._db().execute("SELECT * FROM pending_invites WHERE state='pending' AND validate_after<=?", (now,))
        return list(await cur.fetchall())

    async def finish_pending_invite(self, pending_id: int, valid: bool) -> None:
        await self._db().execute("UPDATE pending_invites SET state=? WHERE id=?", ("valid" if valid else "invalid", pending_id))
        await self._db().commit()

    async def complete_for_trainer(self, guild_id: int, trainer_id: int, community_help: bool) -> None:
        await self.ensure_profile(guild_id, trainer_id)
        if community_help:
            await self._db().execute("UPDATE profiles SET reputation=reputation+25, helped_count=helped_count+1 WHERE guild_id=? AND user_id=?", (guild_id, trainer_id))
        else:
            await self._db().execute("UPDATE profiles SET reputation=reputation+50, trainings_completed=trainings_completed+1 WHERE guild_id=? AND user_id=?", (guild_id, trainer_id))
        await self._db().commit()

    async def add_review(self, guild_id: int, request_id: int, author_id: int, target_id: int, rating: int, comment: str) -> bool:
        try:
            await self._db().execute(
                "INSERT INTO reviews(guild_id,request_id,author_id,target_id,rating,comment,created_at) VALUES (?,?,?,?,?,?,?)",
                (guild_id, request_id, author_id, target_id, rating, comment, int(time.time())),
            )
            await self.ensure_profile(guild_id, target_id)
            await self._db().execute("UPDATE profiles SET reviews_count=reviews_count+1, rating_sum=rating_sum+? WHERE guild_id=? AND user_id=?", (rating, guild_id, target_id))
            await self._db().commit()
            return True
        except aiosqlite.IntegrityError:
            await self._db().rollback()
            return False

    async def add_favorite(self, guild_id: int, user_id: int, resource_key: str) -> bool:
        cur = await self._db().execute(
            "INSERT OR IGNORE INTO favorites(guild_id,user_id,resource_key,created_at) VALUES (?,?,?,?)",
            (guild_id, user_id, resource_key, int(time.time())),
        )
        await self._db().commit()
        return cur.rowcount > 0

    async def remove_favorite(self, guild_id: int, user_id: int, resource_key: str) -> bool:
        cur = await self._db().execute("DELETE FROM favorites WHERE guild_id=? AND user_id=? AND resource_key=?", (guild_id, user_id, resource_key))
        await self._db().commit()
        return cur.rowcount > 0

    async def favorites(self, guild_id: int, user_id: int) -> list[str]:
        cur = await self._db().execute("SELECT resource_key FROM favorites WHERE guild_id=? AND user_id=? ORDER BY created_at DESC", (guild_id, user_id))
        return [str(row["resource_key"]) for row in await cur.fetchall()]

    async def submit_challenge(self, guild_id: int, user_id: int, challenge_key: str, proof: str) -> int | None:
        try:
            cur = await self._db().execute(
                "INSERT INTO challenge_submissions(guild_id,user_id,challenge_key,proof,created_at) VALUES (?,?,?,?,?)",
                (guild_id, user_id, challenge_key, proof, int(time.time())),
            )
            await self._db().commit()
            return int(cur.lastrowid)
        except aiosqlite.IntegrityError:
            await self._db().rollback()
            return None

    async def challenge_submission(self, submission_id: int) -> aiosqlite.Row | None:
        cur = await self._db().execute("SELECT * FROM challenge_submissions WHERE id=?", (submission_id,))
        return await cur.fetchone()

    async def resolve_challenge(self, submission_id: int, reviewer_id: int, accepted: bool) -> bool:
        cur = await self._db().execute(
            "UPDATE challenge_submissions SET status=?, reviewer_id=? WHERE id=? AND status='pending'",
            ("accepted" if accepted else "rejected", reviewer_id, submission_id),
        )
        await self._db().commit()
        return cur.rowcount > 0

    async def create_mentorship(self, guild_id: int, student_id: int, topic: str) -> int | None:
        cur = await self._db().execute(
            "SELECT id FROM mentorships WHERE guild_id=? AND student_id=? AND status IN ('open','active') ORDER BY id DESC LIMIT 1",
            (guild_id, student_id),
        )
        if await cur.fetchone():
            return None
        created = await self._db().execute(
            "INSERT INTO mentorships(guild_id,student_id,topic,created_at) VALUES (?,?,?,?)",
            (guild_id, student_id, topic, int(time.time())),
        )
        await self._db().commit()
        return int(created.lastrowid)

    async def mentorship(self, mentorship_id: int) -> aiosqlite.Row | None:
        cur = await self._db().execute("SELECT * FROM mentorships WHERE id=?", (mentorship_id,))
        return await cur.fetchone()

    async def claim_mentorship(self, mentorship_id: int, mentor_id: int) -> bool:
        cur = await self._db().execute(
            "UPDATE mentorships SET mentor_id=?, status='active' WHERE id=? AND status='open' AND mentor_id IS NULL",
            (mentor_id, mentorship_id),
        )
        await self._db().commit()
        return cur.rowcount > 0

    async def close_mentorship(self, mentorship_id: int) -> bool:
        cur = await self._db().execute("UPDATE mentorships SET status='completed' WHERE id=? AND status='active'", (mentorship_id,))
        await self._db().commit()
        return cur.rowcount > 0

    async def create_application(
        self,
        guild_id: int,
        user_id: int,
        target_role: str,
        experience: str,
        skills: str,
        availability: str,
    ) -> int | None:
        try:
            cur = await self._db().execute(
                """INSERT INTO applications(guild_id,user_id,target_role,experience,skills,availability,created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (guild_id, user_id, target_role, experience, skills, availability, int(time.time())),
            )
            await self._db().commit()
            return int(cur.lastrowid)
        except aiosqlite.IntegrityError:
            await self._db().rollback()
            return None

    async def application(self, application_id: int) -> aiosqlite.Row | None:
        cur = await self._db().execute("SELECT * FROM applications WHERE id=?", (application_id,))
        return await cur.fetchone()

    async def resolve_application(
        self,
        application_id: int,
        reviewer_id: int,
        accepted: bool,
        reason: str = "",
    ) -> bool:
        cur = await self._db().execute(
            """UPDATE applications
               SET status=?, reviewer_id=?, review_reason=?
               WHERE id=? AND status='pending'""",
            ("accepted" if accepted else "rejected", reviewer_id, reason[:500], application_id),
        )
        await self._db().commit()
        return cur.rowcount > 0

    async def pending_applications(self, guild_id: int, limit: int = 20) -> list[aiosqlite.Row]:
        cur = await self._db().execute(
            "SELECT * FROM applications WHERE guild_id=? AND status='pending' ORDER BY created_at ASC LIMIT ?",
            (guild_id, limit),
        )
        return list(await cur.fetchall())

    async def create_reminder(
        self,
        guild_id: int,
        request_id: int,
        channel_id: int,
        user_id: int,
        trainer_id: int | None,
        remind_at: int,
    ) -> int:
        await self._db().execute(
            "UPDATE reminders SET state='cancelled' WHERE request_id=? AND state='pending'",
            (request_id,),
        )
        cur = await self._db().execute(
            """INSERT INTO reminders(guild_id,request_id,channel_id,user_id,trainer_id,remind_at,created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (guild_id, request_id, channel_id, user_id, trainer_id, remind_at, int(time.time())),
        )
        await self._db().commit()
        return int(cur.lastrowid)

    async def cancel_reminders_for_request(self, request_id: int) -> int:
        cur = await self._db().execute(
            "UPDATE reminders SET state='cancelled' WHERE request_id=? AND state='pending'",
            (request_id,),
        )
        await self._db().commit()
        return cur.rowcount

    async def due_reminders(self, now: int, limit: int = 50) -> list[aiosqlite.Row]:
        cur = await self._db().execute(
            "SELECT * FROM reminders WHERE state='pending' AND remind_at<=? ORDER BY remind_at ASC LIMIT ?",
            (now, limit),
        )
        return list(await cur.fetchall())

    async def finish_reminder(self, reminder_id: int, state: str = "sent") -> bool:
        if state not in {"sent", "failed", "cancelled"}:
            raise ValueError("Invalid reminder state")
        cur = await self._db().execute(
            "UPDATE reminders SET state=? WHERE id=? AND state='pending'",
            (state, reminder_id),
        )
        await self._db().commit()
        return cur.rowcount > 0

    async def dashboard_stats(self, guild_id: int) -> dict[str, int | float]:
        queries = {
            "open_requests": "SELECT COUNT(*) AS n FROM requests WHERE guild_id=? AND status IN ('open','assigned','in_progress','payment_pending')",
            "active_trainings": "SELECT COUNT(*) AS n FROM requests WHERE guild_id=? AND status IN ('assigned','in_progress')",
            "pending_challenges": "SELECT COUNT(*) AS n FROM challenge_submissions WHERE guild_id=? AND status='pending'",
            "open_mentorships": "SELECT COUNT(*) AS n FROM mentorships WHERE guild_id=? AND status IN ('open','active')",
            "available_helpers": "SELECT COUNT(*) AS n FROM profiles WHERE guild_id=? AND helper_available=1",
            "pending_applications": "SELECT COUNT(*) AS n FROM applications WHERE guild_id=? AND status='pending'",
            "pending_reminders": "SELECT COUNT(*) AS n FROM reminders WHERE guild_id=? AND state='pending'",
        }
        stats: dict[str, int | float] = {}
        for key, sql in queries.items():
            cur = await self._db().execute(sql, (guild_id,))
            row = await cur.fetchone()
            stats[key] = int(row["n"]) if row else 0
        cur = await self._db().execute("SELECT COUNT(*) AS n, COALESCE(AVG(rating),0) AS avg_rating FROM reviews WHERE guild_id=?", (guild_id,))
        row = await cur.fetchone()
        stats["reviews"] = int(row["n"]) if row else 0
        stats["avg_rating"] = float(row["avg_rating"]) if row else 0.0
        return stats

    async def leaderboard(self, guild_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        cur = await self._db().execute(
            "SELECT * FROM profiles WHERE guild_id=? ORDER BY reputation DESC, helped_count DESC, trainings_completed DESC LIMIT ?",
            (guild_id, limit),
        )
        return list(await cur.fetchall())
