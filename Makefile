up:        ; docker compose up -d neo4j kb-api streamlit-ui
load:      ; docker compose run --rm loader
			 docker compose build loader
			 docker compose build --no-cache loader
			 docker compose run --rm loader python -m scripts.run_schema
			 docker compose --profile local-db up -d neo4j
docker compose down
docker compose up -d

builder klasik: ; docker-compose up -d
membuat kontainer baru dari awal: ;
			 docker compose up -d --force-recreate
remove dlu: ; 
			docker compose down --remove-orphans
			docker compose --profile local-db down --remove-orphans

hapus plugin korup: ; Remove-Item -Force "$env:USERPROFILE\.docker\cli-plugins\docker-buildx.exe" -ErrorAction SilentlyContinue

cek log: ; docker compose logs --tail 50 kb-api
seed:      ; python -m scripts.generate_seed_qa
schema:    ; python -m scripts.run_schema
ingest:    ; python -m scripts.run_ingest
test:      ; python -m pytest -q tests
reset:     ; docker compose down -v
stop:      ; docker compose stop

streamlit  ; streamlit run ui/app.py

jika Error response from daemon: failed to set up container networking: 
docker rm -f bencana-neo4j
docker network prune -f

docker compose restart streamlit-ui

docker compose build streamlit-ui
docker compose up -d

wsl --shutdown

MATCH (n) DETACH DELETE n;

cd ~/kb_disaster/kb_disaster
ls

DROP CONSTRAINT answer_id IF EXISTS;
DROP CONSTRAINT category_name IF EXISTS;
DROP CONSTRAINT chunk_id IF EXISTS;
DROP CONSTRAINT document_id IF EXISTS;
DROP CONSTRAINT location_name IF EXISTS;
DROP CONSTRAINT org_id IF EXISTS;
DROP CONSTRAINT question_id IF EXISTS;
DROP CONSTRAINT reference_id IF EXISTS;
DROP CONSTRAINT step_id IF EXISTS;
DROP CONSTRAINT subcategory_name IF EXISTS;
DROP CONSTRAINT tag_name IF EXISTS;

DROP INDEX chunk_damage_status IF EXISTS;
DROP INDEX chunk_doc IF EXISTS;
DROP INDEX chunk_inundation IF EXISTS;
DROP INDEX chunk_level IF EXISTS;
DROP INDEX chunk_section IF EXISTS;
DROP INDEX chunk_text_ft IF EXISTS;
DROP INDEX document_category IF EXISTS;
DROP INDEX document_domain IF EXISTS;
DROP INDEX document_file_type IF EXISTS;
DROP INDEX document_ft IF EXISTS;
DROP INDEX document_year IF EXISTS;
DROP INDEX location_ft IF EXISTS;
DROP INDEX location_level IF EXISTS;
DROP INDEX organization_ft IF EXISTS;
DROP INDEX organization_level IF EXISTS;
DROP INDEX question_text_ft IF EXISTS;
DROP INDEX tag_kind IF EXISTS;