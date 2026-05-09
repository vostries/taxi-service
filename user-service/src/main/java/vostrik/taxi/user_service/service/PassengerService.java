package vostrik.taxi.user_service.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import vostrik.taxi.user_service.dto.PassengerRequest;
import vostrik.taxi.user_service.dto.PassengerResponse;
import vostrik.taxi.user_service.entity.Passenger;
import vostrik.taxi.user_service.exception.BadRequestException;
import vostrik.taxi.user_service.exception.ResourceNotFoundException;
import vostrik.taxi.user_service.repository.PassengerRepository;

@Service
@RequiredArgsConstructor
public class PassengerService {

    private final PassengerRepository passengerRepository;

    public PassengerResponse createPassenger(PassengerRequest request) {
        if (passengerRepository.existsByEmail(request.getEmail())) {
            throw new BadRequestException("Passenger with this email already exists");
        }
        Passenger passenger = Passenger.builder()
                .name(request.getName())
                .email(request.getEmail())
                .phone(request.getPhone())
                .build();
        passenger = passengerRepository.save(passenger);
        return toResponse(passenger);
    }

    public PassengerResponse getPassenger(Long id) {
        Passenger passenger = passengerRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Passenger not found: " + id));
        return toResponse(passenger);
    }

    public boolean passengerExists(Long id) {
        return passengerRepository.existsById(id);
    }

    private PassengerResponse toResponse(Passenger p) {
        return PassengerResponse.builder()
                .id(p.getId())
                .name(p.getName())
                .email(p.getEmail())
                .phone(p.getPhone())
                .createdAt(p.getCreatedAt())
                .build();
    }
}
