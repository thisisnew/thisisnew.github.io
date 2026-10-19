-- MySQL/InnoDB learning schema. Run only in a dedicated test database.
CREATE TABLE stock (
  sku VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  qty BIGINT NOT NULL,
  PRIMARY KEY (sku)
) ENGINE=InnoDB;
CREATE TABLE processed_event (
  consumer_name VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  event_id VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  PRIMARY KEY (consumer_name, event_id)
) ENGINE=InnoDB;
INSERT INTO stock(sku,qty) VALUES ('SKU-A',0);
