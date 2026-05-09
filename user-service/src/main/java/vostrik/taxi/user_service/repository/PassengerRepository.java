package vostrik.taxi.user_service.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vostrik.taxi.user_service.entity.Passenger;

public interface PassengerRepository extends JpaRepository<Passenger, Long> {
    boolean existsByEmail(String email);
}
