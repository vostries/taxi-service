package vostrik.taxi.user_service.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import vostrik.taxi.user_service.dto.PassengerRequest;
import vostrik.taxi.user_service.dto.PassengerResponse;
import vostrik.taxi.user_service.service.PassengerService;

@RestController
@RequestMapping("/passengers")
@RequiredArgsConstructor
public class PassengerController {

    private final PassengerService passengerService;

    @PostMapping
    public ResponseEntity<PassengerResponse> create(@Valid @RequestBody PassengerRequest request) {
        return ResponseEntity.status(201).body(passengerService.createPassenger(request));
    }

    @GetMapping("/{id}")
    public ResponseEntity<PassengerResponse> getById(@PathVariable Long id) {
        return ResponseEntity.ok(passengerService.getPassenger(id));
    }
}
