-- Adminer 5.4.2 PostgreSQL 16.13 dump

\connect "app_db";

CREATE SCHEMA app_schema;

SET search_path TO app_schema;

CREATE SEQUENCE "app_schema".exercise_instructions_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE "app_schema"."exercise_instructions" (
    "id" integer DEFAULT nextval('exercise_instructions_id_seq') NOT NULL,
    "exercise_id" text,
    "step_number" integer,
    "instruction" text,
    CONSTRAINT "exercise_instructions_pkey" PRIMARY KEY ("id")
)
WITH (oids = false);


CREATE SEQUENCE "app_schema".exercise_secondary_muscles_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE "app_schema"."exercise_secondary_muscles" (
    "id" integer DEFAULT nextval('exercise_secondary_muscles_id_seq') NOT NULL,
    "exercise_id" text,
    "muscle" text NOT NULL,
    CONSTRAINT "exercise_secondary_muscles_pkey" PRIMARY KEY ("id")
)
WITH (oids = false);


CREATE TABLE "app_schema"."exercises" (
    "id" text NOT NULL,
    "name" text NOT NULL,
    "body_part" text,
    "equipment" text,
    "gif_url" text,
    "target" text,
    CONSTRAINT "exercises_pkey" PRIMARY KEY ("id")
)
WITH (oids = false);


ALTER TABLE ONLY "app_schema"."exercise_instructions" ADD CONSTRAINT "exercise_instructions_exercise_id_fkey" FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE;

ALTER TABLE ONLY "app_schema"."exercise_secondary_muscles" ADD CONSTRAINT "exercise_secondary_muscles_exercise_id_fkey" FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE;

-- 2026-03-08 06:59:31 UTC
