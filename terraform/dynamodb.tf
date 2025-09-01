# dynamodb.tf
module "towary_table" {
  source     = "./modules/dynamo_db_tables"
  table_name = "towary"
  hash_key   = "ID_TOWARU"
  range_key  = "DATA_MODYFIKACJI"

  attributes = [
    { name = "ID_TOWARU", type = "N" },
    { name = "DATA_MODYFIKACJI", type = "S" },
    { name = "NAZWA_TOWARU", type = "S" },
    { name = "NAZWA_VAT", type = "S" },
    { name = "DATA_UTWORZENIA", type = "S" }
  ]

  global_secondary_indexes = [
    {
      name            = "nazwa_towaru_index"
      hash_key        = "NAZWA_TOWARU"
      projection_type = "ALL"
    },
    {
      name            = "data_utworzenia_index"
      hash_key        = "DATA_UTWORZENIA"
      projection_type = "ALL"
    },
    {
      name            = "nazwa_vat_index"
      hash_key        = "NAZWA_VAT"
      projection_type = "ALL"
    }
  ]
}

module "ceny_towarow_table" {
  source     = "./modules/dynamo_db_tables"
  table_name = "ceny_towarow"
  hash_key   = "ID_TOWARU"
  range_key  = "TS"

  attributes = [
    { name = "ID_TOWARU", type = "N" },
    { name = "TS", type = "N" },
    { name = "CENA", type = "N" },
    { name = "FLAGA", type = "S" },
    { name = "CENA_ZAKUPU", type = "N" },
    { name = "MARZA", type = "N" },
    { name = "UPUST", type = "N" }
  ]

  global_secondary_indexes = [
    { name = "gsi_cena", hash_key = "ID_TOWARU", range_key = "CENA", projection_type = "ALL" },
    { name = "gsi_flaga", hash_key = "ID_TOWARU", range_key = "FLAGA", projection_type = "ALL" },
    { name = "gsi_cena_zak", hash_key = "ID_TOWARU", range_key = "CENA_ZAKUPU", projection_type = "ALL" },
    { name = "gsi_marza", hash_key = "ID_TOWARU", range_key = "MARZA", projection_type = "ALL" },
    { name = "gsi_upust", hash_key = "ID_TOWARU", range_key = "UPUST", projection_type = "ALL" }
  ]
}

module "akt_stan_mag_table" {
  source     = "./modules/dynamo_db_tables"
  table_name = "akt_stan_mag"
  hash_key   = "ID_TOWARU"
  range_key  = "ID_MAGAZYNU"

  attributes = [
    { name = "ID_TOWARU", type = "N" },
    { name = "ID_MAGAZYNU", type = "S" },
    { name = "ILOSC", type = "N" },
    { name = "ILOSC_ZAREZERWOWANA", type = "N" }
  ]

  global_secondary_indexes = [
    { name = "ilosc_index", hash_key = "ILOSC", projection_type = "ALL" },
    { name = "ilosc_zarezerwowana_index", hash_key = "ILOSC_ZAREZERWOWANA", projection_type = "ALL" },
    { name = "id_magazynu_index", hash_key = "ID_MAGAZYNU", projection_type = "ALL" }
  ]
}

module "klasy_towarow_table" {
  source     = "./modules/dynamo_db_tables"
  table_name = "klasy_towarow"
  hash_key   = "ID_KLASY"

  attributes = [
    { name = "ID_KLASY", type = "N" },
    { name = "ID_TOWARU", type = "N" },
    { name = "ID_KLASY_NADRZ", type = "N" },
    { name = "NAZWA_KLASY", type = "S" },
    { name = "CZY_AKTYWNY", type = "S" },
    { name = "TS", type = "N" }
  ]

  global_secondary_indexes = [
    { name = "id_towaru_index", hash_key = "ID_TOWARU", projection_type = "ALL" },
    { name = "id_klasy_nadrz_index", hash_key = "ID_KLASY_NADRZ", projection_type = "ALL" },
    { name = "nazwa_klasy_index", hash_key = "NAZWA_KLASY", projection_type = "ALL" },
    { name = "czy_aktywny_index", hash_key = "CZY_AKTYWNY", projection_type = "ALL" },
    { name = "ts_index", hash_key = "TS", projection_type = "ALL" }
  ]
}

module "users_table" {
  source     = "./modules/dynamo_db_tables"
  table_name = "users"
  hash_key   = "user_id"

  attributes = [
    { name = "user_id",      type = "S" },
    { name = "email",        type = "S" },
    { name = "auth_type",    type = "S" },
    { name = "first_name",   type = "S" },
    { name = "surname",      type = "S" },
    { name = "created_at",   type = "S" },  # mandatory
    { name = "updated_at",   type = "S" }   # mandatory
  ]

  global_secondary_indexes = [
    {
      name            = "email_index"
      hash_key        = "email"
      projection_type = "ALL"
    },
    {
      name            = "auth_type_index"
      hash_key        = "auth_type"
      projection_type = "ALL"
    },
    {
      name            = "first_name_index"
      hash_key        = "first_name"
      projection_type = "ALL"
    },
    {
      name            = "surname_index"
      hash_key        = "surname"
      projection_type = "ALL"
    },
    {
      name            = "created_at_index"
      hash_key        = "created_at"
      projection_type = "ALL"
    },
    {
      name            = "updated_at_index"
      hash_key        = "updated_at"
      projection_type = "ALL"
    }
  ]
}

module "magazyny_table" {
  source     = "./modules/dynamo_db_tables"
  table_name = "magazyny"
  hash_key   = "ID_MAGAZYNU"

  # Only declare attributes used in keys / GSIs
  attributes = [
    { name = "ID_MAGAZYNU", type = "S" }
  ]

  # No GSIs needed right now
  global_secondary_indexes = []
}