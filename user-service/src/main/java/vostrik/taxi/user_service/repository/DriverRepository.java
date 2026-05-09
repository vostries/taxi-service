package vostrik.taxi.user_service.repository;

import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import vostrik.taxi.user_service.entity.Driver;
import vostrik.taxi.user_service.entity.DriverStatus;

import java.util.List;
import java.util.Optional;

public interface DriverRepository extends JpaRepository<Driver, Long> {
    List<Driver> findByStatus(DriverStatus status);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    Optional<Driver> findFirstByStatusOrderByIdAsc(DriverStatus status);

    boolean existsByEmail(String email);
}
