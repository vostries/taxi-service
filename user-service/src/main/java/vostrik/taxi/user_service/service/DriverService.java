package vostrik.taxi.user_service.service;

import lombok.RequiredArgsConstructor;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vostrik.taxi.user_service.dto.DriverRequest;
import vostrik.taxi.user_service.dto.DriverResponse;
import vostrik.taxi.user_service.entity.Driver;
import vostrik.taxi.user_service.entity.DriverStatus;
import vostrik.taxi.user_service.exception.BadRequestException;
import vostrik.taxi.user_service.exception.ResourceNotFoundException;
import vostrik.taxi.user_service.repository.DriverRepository;

import java.util.List;

@Service
@RequiredArgsConstructor
public class DriverService {

    private final DriverRepository driverRepository;

    @Transactional
    public DriverResponse assignAvailableDriver() {
        Driver driver = driverRepository.findFirstByStatusOrderByIdAsc(DriverStatus.AVAILABLE)
                .orElseThrow(() -> new ResourceNotFoundException("No available drivers"));
        driver.setStatus(DriverStatus.BUSY);
        driver = driverRepository.save(driver);
        return toResponse(driver);
    }

    @CacheEvict(value = "availableDrivers", allEntries = true)
    public DriverResponse createDriver(DriverRequest request) {
        if (driverRepository.existsByEmail(request.getEmail())) {
            throw new BadRequestException("Driver with this email already exists");
        }
        Driver driver = Driver.builder()
                .name(request.getName())
                .email(request.getEmail())
                .phone(request.getPhone())
                .licenseNumber(request.getLicenseNumber())
                .build();
        driver = driverRepository.save(driver);
        return toResponse(driver);
    }

    public DriverResponse getDriver(Long id) {
        Driver driver = driverRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Driver not found: " + id));
        return toResponse(driver);
    }

    @CacheEvict(value = "availableDrivers", allEntries = true)
    public DriverResponse updateDriverStatus(Long id, String status) {
        Driver driver = driverRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Driver not found: " + id));
        driver.setStatus(DriverStatus.valueOf(status));
        driver = driverRepository.save(driver);
        return toResponse(driver);
    }

    @Cacheable(value = "availableDrivers")
    public List<DriverResponse> getAvailableDrivers() {
        return driverRepository.findByStatus(DriverStatus.AVAILABLE)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    private DriverResponse toResponse(Driver d) {
        return DriverResponse.builder()
                .id(d.getId())
                .name(d.getName())
                .email(d.getEmail())
                .phone(d.getPhone())
                .licenseNumber(d.getLicenseNumber())
                .status(d.getStatus().name())
                .createdAt(d.getCreatedAt())
                .build();
    }
}
