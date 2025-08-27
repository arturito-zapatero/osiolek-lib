module "akt_stan_mag_table" {
  source     = "./modules/dynamodb_table"
  table_name = "akt_stan_mag"
  hash_key   = "ID_TOWARU"

  attributes = [
    { name = "ID_TOWARU", type = "N" },
    { name = "ID_MAGAZYNU", type = "S" },
    { name = "ILOSC", type = "N" },
    { name = "ILOSC_ZAREZERWOWANA", type = "N" }
  ]
}