package vostrik.taxi.user_service.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import vostrik.taxi.user_service.dto.DriverRequest;
import vostrik.taxi.user_service.dto.DriverResponse;
import vostrik.taxi.user_service.dto.DriverStatusRequest;
import vostrik.taxi.user_service.service.DriverService;

@RestController
@RequestMapping("/drivers")
@RequiredArgsConstructor
public class DriverController {

    private final DriverService driverService;

    @PostMapping
    public ResponseEntity<DriverResponse> create(@Valid @RequestBody DriverRequest request) {
        return ResponseEntity.status(201).body(driverService.createDriver(request));
    }

    @GetMapping("/{id}")
    public ResponseEntity<DriverResponse> getById(@PathVariable Long id) {
        return ResponseEntity.ok(driverService.getDriver(id));
    }

    @PatchMapping("/{id}/status")
    public ResponseEntity<DriverResponse> updateStatus(@PathVariable Long id,
                                                        @Valid @RequestBody DriverStatusRequest request) {
        return ResponseEntity.ok(driverService.updateDriverStatus(id, request.getStatus()));
    }
}
