--
-- PostgreSQL database dump
--

-- Dumped from database version 14.18 (Ubuntu 14.18-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.18 (Ubuntu 14.18-0ubuntu0.22.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agents; Type: TABLE; Schema: public; Owner: gpt
--

CREATE TABLE public.agents (
    id bigint NOT NULL,
    telegram_id bigint,
    name character varying,
    phone character varying,
    agent_type character varying,
    registered_at timestamp without time zone
);


ALTER TABLE public.agents OWNER TO gpt;

--
-- Name: agents_id_seq; Type: SEQUENCE; Schema: public; Owner: gpt
--

CREATE SEQUENCE public.agents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.agents_id_seq OWNER TO gpt;

--
-- Name: agents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gpt
--

ALTER SEQUENCE public.agents_id_seq OWNED BY public.agents.id;


--
-- Name: companies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.companies (
    inn text NOT NULL,
    data jsonb NOT NULL
);


ALTER TABLE public.companies OWNER TO postgres;

--
-- Name: company; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.company AS
 SELECT companies.inn,
    companies.data
   FROM public.companies;


ALTER TABLE public.company OWNER TO postgres;

--
-- Name: orders; Type: TABLE; Schema: public; Owner: gpt
--

CREATE TABLE public.orders (
    id bigint NOT NULL,
    telegram_id bigint,
    message character varying,
    original_amt bigint,
    final_amt bigint,
    reward_cust bigint,
    reward_exec bigint,
    fee_platform bigint,
    cust_requisites character varying,
    carrier_requisites character varying,
    cars character varying,
    loads character varying,
    unloads character varying,
    pay_terms character varying,
    insurance_policy character varying,
    executor_id bigint,
    driver_fio character varying,
    driver_passport character varying,
    truck_reg character varying,
    trailer_reg character varying,
    driver_license character varying,
    truck_model character varying,
    trailer_model character varying,
    status character varying,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    cust_company_name character varying,
    cust_director character varying
);


ALTER TABLE public.orders OWNER TO gpt;

--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: public; Owner: gpt
--

CREATE SEQUENCE public.orders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.orders_id_seq OWNER TO gpt;

--
-- Name: orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gpt
--

ALTER SEQUENCE public.orders_id_seq OWNED BY public.orders.id;


--
-- Name: agents id; Type: DEFAULT; Schema: public; Owner: gpt
--

ALTER TABLE ONLY public.agents ALTER COLUMN id SET DEFAULT nextval('public.agents_id_seq'::regclass);


--
-- Name: orders id; Type: DEFAULT; Schema: public; Owner: gpt
--

ALTER TABLE ONLY public.orders ALTER COLUMN id SET DEFAULT nextval('public.orders_id_seq'::regclass);


--
-- Data for Name: agents; Type: TABLE DATA; Schema: public; Owner: gpt
--

COPY public.agents (id, telegram_id, name, phone, agent_type, registered_at) FROM stdin;
1	6835069941	Главный админ	\N	admin	\N
2	7823236991	Тезник		исполнитель	2025-05-19 07:42:15.872568
3	5799866832	Максим Федорович		исполнитель	2025-05-19 08:38:32.20777
4	6930567432	ТехноЛогистика.КБР		заказчик	2025-05-19 08:39:32.738204
\.


--
-- Data for Name: companies; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.companies (inn, data) FROM stdin;
50505050	{"inn": "50505050", "kpp": "344934849", "name": "ООО \\"пять-ноль\\"", "director": "🏢 Компания «ООО \\"пять-ноль\\"» найдена.\\nИспользовать сохранённые реквизиты?"}
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: gpt
--

COPY public.orders (id, telegram_id, message, original_amt, final_amt, reward_cust, reward_exec, fee_platform, cust_requisites, carrier_requisites, cars, loads, unloads, pay_terms, insurance_policy, executor_id, driver_fio, driver_passport, truck_reg, trailer_reg, driver_license, truck_model, trailer_model, status, created_at, updated_at, cust_company_name, cust_director) FROM stdin;
1	6835069941	Нальчик — Москва, Лада Гранта, 7 авто, 100 000 руб	100000	88000	5000	3000	4000	ИНН 50505050, КПП 344934849, Юридический адрес: Нальчик, Ленина 1	ИНН 50505050, КПП 344934849, Юридический адрес: Нальчик, Ленина 1	[]	\N	\N	Наличными, на выгрузке		7823236991	Иванов Сергей Николаевич	3636 37363783	\N	\N		\N	\N	paid	2025-05-28 09:20:47.727606	2025-05-28 09:24:10.840438	ООО "пять-ноль"	🏢 Компания «ООО "пять-ноль"» найдена.\nИспользовать сохранённые реквизиты?
2	6835069941	Нальчик — Москва, 29.05 – 03.06, Лада Гранта, 3 авто, 150 000 руб	150000	132000	7500	4500	6000	ИНН 50505050, КПП 344934849	\N	[]	[{"place": "Нальчик, Кирова 1", "date": "29.05", "contact": "", "vins": []}]	[{"place": "Москва, Ленина 1", "date": "03.06", "contact": "", "vins": []}]	Наличными, на выгрузке	\N	\N	\N	\N	\N	\N	\N	\N	\N	active	2025-05-28 10:09:30.501467	\N	ООО "пять-ноль"	🏢 Компания «ООО "пять-ноль"» найдена.\nИспользовать сохранённые реквизиты?
3	6835069941	Нальчик — Москва, 29.05 – 02.06, Лада Гранта, 3 аво, 140 000 руб	140000	123200	7000	4200	5600	ИНН 50505050, КПП 344934849	\N	[]	[{"place": "Нальчик, Кирова 1", "date": "29.05", "contact": "", "vins": []}]	[{"place": "Москва, Ленина 1", "date": "02.06", "contact": "", "vins": []}]	Наличными, на выгрузке	\N	\N	\N	\N	\N	\N	\N	\N	\N	active	2025-05-28 10:12:20.985868	\N	ООО "пять-ноль"	🏢 Компания «ООО "пять-ноль"» найдена.\nИспользовать сохранённые реквизиты?
4	6835069941	Нальчик — Моква, 29.05 – 02.06, Лада Гранта, 3 авто, 200 000 руб, Наличными, на выгрзке	200000	176000	10000	6000	8000	ИНН 50505050, КПП 344934849	\N	[]	[{"place": "Нальчик, Кирова 1", "date": "29.05", "contact": "", "vins": []}]	[{"place": "Моква, Ленина 1", "date": "02.06", "contact": "", "vins": []}]	Наличными, на выгрзке	\N	\N	\N	\N	\N	\N	\N	\N	\N	active	2025-05-28 10:13:52.186322	\N	ООО "пять-ноль"	🏢 Компания «ООО "пять-ноль"» найдена.\nИспользовать сохранённые реквизиты?
5	6835069941	Нальчик — Москва, 28.05.2025 – 02.06.2025, Лада Гранта, 3 авто, 200 000 руб, Наличными, на выгрузке	2025	1782	101	60	81	ИНН 50505050, КПП 344934849	\N	[]	[{"place": "Нальчик, Кирова 1", "date": "28.05.2025", "contact": "", "vins": []}]	[{"place": "Москва, Ленина 1", "date": "02.06.2025", "contact": "", "vins": []}]	Наличными, на выгрузке	\N	\N	\N	\N	\N	\N	\N	\N	\N	active	2025-05-28 10:20:19.692073	\N	ООО "пять-ноль"	🏢 Компания «ООО "пять-ноль"» найдена.\nИспользовать сохранённые реквизиты?
6	6835069941	Нальчик — Москва, 29.05.2025 – 02.06.2025, Лада Гранта, 3 авто, 200 000 руб, Наличными, на выгрузке	2025	1782	101	60	81	ИНН 50505050, КПП 344934849	\N	[]	[{"place": "Нальчик, Кирова 1", "date": "29.05.2025", "contact": "", "vins": []}]	[{"place": "Москва, Ленина 1", "date": "02.06.2025", "contact": "", "vins": []}]	Наличными, на выгрузке	\N	\N	\N	\N	\N	\N	\N	\N	\N	active	2025-05-28 10:29:37.068337	\N	ООО "пять-ноль"	🏢 Компания «ООО "пять-ноль"» найдена.\nИспользовать сохранённые реквизиты?
7	6835069941	Нальчик — Москва, 29.05.2025 – 30.05.2025, Лада Гранта, 3 авто, 150 000 рую, Наличными на выгрзуке, 🏆 Ваш бонус: +4 500 ₽	2025	1782	101	60	81	ИНН 50505050, КПП 344934849	\N	[]	[{"place": "Нальчик, Кирова 1", "date": "29.05.2025", "contact": "", "vins": []}]	[{"place": "Москва, Ленина 1", "date": "30.05.2025", "contact": "", "vins": []}]	Наличными на выгрзуке	\N	\N	\N	\N	\N	\N	\N	\N	\N	active	2025-05-28 10:38:51.463464	\N	ООО "пять-ноль"	🏢 Компания «ООО "пять-ноль"» найдена.\nИспользовать сохранённые реквизиты?
\.


--
-- Name: agents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gpt
--

SELECT pg_catalog.setval('public.agents_id_seq', 4, true);


--
-- Name: orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gpt
--

SELECT pg_catalog.setval('public.orders_id_seq', 7, true);


--
-- Name: agents agents_pkey; Type: CONSTRAINT; Schema: public; Owner: gpt
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_pkey PRIMARY KEY (id);


--
-- Name: agents agents_telegram_id_key; Type: CONSTRAINT; Schema: public; Owner: gpt
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_telegram_id_key UNIQUE (telegram_id);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (inn);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: gpt
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: ix_orders_message; Type: INDEX; Schema: public; Owner: gpt
--

CREATE INDEX ix_orders_message ON public.orders USING btree (message);


--
-- PostgreSQL database dump complete
--

